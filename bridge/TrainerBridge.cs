using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using BepInEx;
using UnityEngine;

namespace HollowTrainer;

[Serializable] public class Request {
    public string id, session, operation;
    public double created;
    public float value;
}
[Serializable] public class Lease { public string session; public double timestamp; }
[Serializable] public class Snapshot {
    public int protocol = 1, pid, health, maxHealth, currency;
    public string game, version, session, lastCommand = "", error = "";
    public double timestamp;
    public bool ready, paused, invincible, healthLock, resource, jump, tools, noclip, dash, fastAttack;
    public float runtimeScale, actualRunSpeed;
    public int actualDamage, shards;
    public float damage = 1, speed = 1, move = 1;
}

// A file-only allowlisted bridge. All game access happens on Unity's main thread.
// No listener, command execution, arbitrary member names, or remote API.
[BepInPlugin("local.hollowtrainer.bridge", "Hollow Trainer Bridge", "0.1.0")]
[BepInDependency("io.github.themulhima.debugmod", BepInDependency.DependencyFlags.SoftDependency)]
[BepInDependency("io.github.hk-speedrunning.debugmod", BepInDependency.DependencyFlags.SoftDependency)]
public sealed class TrainerBridge : BaseUnityPlugin {
    const BindingFlags Flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance;
    Type mod, funcs, playerType, heroType, gameType, silkTime;
    object player, hero, manager;
    string folder;
    bool silk, initialized, lastReady, hadLease;
    float nextPoll, damageBase, damageOriginal, speedOriginal = 1;
    object ownedPlayer;
    readonly Dictionary<string, bool> original = new();
    readonly Snapshot state = new();
    readonly HashSet<string> seen = new();
    bool damageOwned, speedOwned;
    bool deferredTimeRemoval;
    object movementHero;
    readonly Dictionary<string, float> movementOriginal = new();
    static double Now => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

    static Type Find(string name) => AppDomain.CurrentDomain.GetAssemblies()
        .Select(a => a.GetType(name, false)).FirstOrDefault(t => t != null);
    static object Get(object target, string name) {
        if (target == null) return null;
        var type = target as Type ?? target.GetType();
        var instance = target is Type ? null : target;
        var field = type.GetField(name, Flags);
        return field != null ? field.GetValue(instance) : type.GetProperty(name, Flags)?.GetValue(instance);
    }
    static void Set(object target, string name, object value) {
        var type = target as Type ?? target.GetType();
        var instance = target is Type ? null : target;
        var field = type.GetField(name, Flags);
        if (field != null) { field.SetValue(instance, Convert.ChangeType(value, field.FieldType)); return; }
        var property = type.GetProperty(name, Flags) ?? throw new MissingMemberException(type.Name, name);
        property.SetValue(instance, Convert.ChangeType(value, property.PropertyType));
    }
    static object Call(object target, string name, params object[] args) {
        var type = target as Type ?? target.GetType();
        var method = type.GetMethods(Flags).FirstOrDefault(m => m.Name == name && m.GetParameters().Length == args.Length)
            ?? throw new MissingMethodException(type.Name, name);
        return method.Invoke(target is Type ? null : target, args);
    }
    static bool Bool(object value) => value != null && Convert.ToBoolean(value);
    static int Int(object value) => value == null ? 0 : Convert.ToInt32(value);
    static float Float(object value) => value == null ? 0 : Convert.ToSingle(value);

    void Awake() {
        silk = Application.productName.IndexOf("Silksong", StringComparison.OrdinalIgnoreCase) >= 0;
        state.game = silk ? "silksong" : "knight";
        state.version = Application.version;
        state.session = Guid.NewGuid().ToString("N");
        state.pid = System.Diagnostics.Process.GetCurrentProcess().Id;
        folder = Environment.GetEnvironmentVariable("HOLLOW_TRAINER_IPC");
        if (string.IsNullOrEmpty(folder)) folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal),
            "Library", "Application Support", "Hollow Mac Trainer", "runtime", state.game);
        Directory.CreateDirectory(folder);
        Application.runInBackground = true;
        Logger.LogInfo("Bridge ready: " + state.game + " session " + state.session);
    }

    void Initialize() {
        mod = Find("DebugMod.DebugMod"); funcs = Find("DebugMod.BindableFunctions");
        playerType = Find("PlayerData"); heroType = Find("HeroController"); gameType = Find("GameManager");
        silkTime = Find("DebugMod.MonoBehaviours.TimeScale");
        if (mod == null || funcs == null || playerType == null) throw new InvalidOperationException("DebugMod не загрузился. Проверьте журнал игры.");
        // External UI is primary; F2 remains available. Hide diagnostic overlays, including during cinematics.
        var settings = Get(mod, "settings");
        if (settings == null) throw new InvalidOperationException("Ожидание DebugMod");
        foreach (var key in new[] {"InfoPanelVisible", "EnemiesPanelVisible", "ConsoleVisible", "SaveStatePanelVisible",
                                  "MainPanelVisible", "TopMenuVisible", "HelpPanelVisible", "MinInfoPanelVisible"})
            if (settings.GetType().GetMember(key, Flags).Length > 0) Set(settings, key, false);
        initialized = true;
    }

    void Update() {
        try {
            if (state.ready && hero is Component activeHero && activeHero != null) {
                if (state.dash) { Set(hero, "dashCooldownTimer", 0f); Set(hero, "airDashed", false); }
                if (state.fastAttack) Set(hero, "attack_cooldown", 0f);
            }
            if (deferredTimeRemoval && manager is Component gm && gm != null && !Bool(Call(manager, "IsGamePaused"))) {
                var component = gm.GetComponent(Find("DebugMod.MonoBehaviours.TimeScale"));
                if (component != null) Destroy(component);
                deferredTimeRemoval = false;
            }
        } catch (Exception e) { state.dash = state.fastAttack = false; state.error = RootMessage(e); }
        if (Time.realtimeSinceStartup < nextPoll) return;
        nextPoll = Time.realtimeSinceStartup + .15f;
        try {
            if (!initialized) Initialize();
            player = Get(playerType, "instance"); hero = Get(heroType, "instance"); manager = Get(gameType, "instance");
            bool ready = player != null && hero is Component component && component != null &&
                manager != null && Bool(Call(manager, "IsGameplayScene"));
            if ((lastReady && !ready) || (ownedPlayer != null && !ReferenceEquals(ownedPlayer, player))) ResetOwned();
            state.ready = ready;
            lastReady = ready;
            bool live = LeaseLive();
            if (!live && (hadLease || original.Count > 0 || damageOwned || speedOwned || movementOriginal.Count > 0)) ResetOwned();
            hadLease = live;
            ReadCommand(live);
            ReadState();
        } catch (Exception e) { state.error = RootMessage(e); state.ready = false; }
        try { WriteState(); } catch (Exception e) { Logger.LogWarning("Status: " + e.Message); }
    }

    bool LeaseLive() {
        try {
            var p = Path.Combine(folder, "lease.json");
            if (new FileInfo(p).Length > 4096) return false;
            var lease = JsonUtility.FromJson<Lease>(File.ReadAllText(p));
            double age = Now - lease.timestamp;
            return lease.session == state.session && age >= -2 && age < 4;
        } catch { return false; }
    }

    void ReadCommand(bool live) {
        var path = Path.Combine(folder, "request.json");
        if (!File.Exists(path)) return;
        if (new FileInfo(path).Length > 4096) return;
        var request = JsonUtility.FromJson<Request>(File.ReadAllText(path));
        if (request == null || string.IsNullOrEmpty(request.id) || seen.Contains(request.id)) return;
        // Never replay currency operations; IDs remembered for this process, including rejected requests.
        if (seen.Count > 20000) throw new InvalidOperationException("Слишком много запросов: перезапустите игру.");
        seen.Add(request.id);
        state.lastCommand = request.id;
        state.error = "";
        try {
            if (request.session != state.session || !live || Now - request.created > 5 || Now - request.created < -2)
                throw new InvalidOperationException("Сеанс изменился. Повторите действие.");
            if (request.operation == "reset") { ResetOwned(); return; }
            if (!state.ready) throw new InvalidOperationException("Сначала загрузите сохранение и дождитесь управления героем.");
            if (float.IsNaN(request.value) || float.IsInfinity(request.value)) throw new ArgumentException("Неверное значение");
            Apply(request.operation, request.value);
            Logger.LogInfo("Applied " + request.operation + " = " + request.value);
        } catch (Exception e) { state.error = RootMessage(e); Logger.LogWarning(state.error); }
    }

    bool ReadToggle(string key) => key switch {
        "invincible" => Bool(Get(mod, "playerInvincible")),
        "health" => Bool(Get(mod, "infiniteHP")),
        "resource" => Bool(Get(mod, silk ? "infiniteSilk" : "infiniteSoul")),
        "jump" => Bool(Get(player, "infiniteAirJump")),
        "tools" => silk && Bool(Get(mod, "infiniteTools")),
        "noclip" => Bool(Get(mod, "noclip")),
        _ => throw new ArgumentException("Неизвестный переключатель")
    };
    void SetToggle(string key, bool value) {
        if (ReadToggle(key) == value) return;
        string method = key switch {
            "invincible" => "ToggleInvincibility", "health" => "ToggleInfiniteHP",
            "resource" => silk ? "ToggleInfiniteSilk" : "ToggleInfiniteSoul",
            "jump" => "ToggleInfiniteJump", "tools" when silk => "ToggleInfiniteTools",
            "noclip" => "ToggleNoclip", _ => throw new ArgumentException("Недоступный переключатель")
        };
        Call(funcs, method);
    }
    void Apply(string key, float value) {
        if (key == "dash" || key == "fastAttack") {
            if (value != 0 && value != 1) throw new ArgumentException("Переключатель: 0 или 1");
            if (key == "dash") state.dash = value == 1; else state.fastAttack = value == 1;
        } else if (key == "move") {
            if (value < .5f || value > 3) throw new ArgumentException("Скорость движения: от 0.5 до 3×");
            if (movementHero != hero) { RestoreMovement(); movementHero = hero; }
            foreach (var field in new[] {"RUN_SPEED", "RUN_SPEED_CH", "RUN_SPEED_CH_COMBO", "WALK_SPEED"}) {
                if (hero.GetType().GetField(field, Flags) == null) continue;
                if (!movementOriginal.ContainsKey(field)) movementOriginal[field] = Float(Get(hero, field));
                Set(hero, field, movementOriginal[field] * value);
            }
            state.move = value;
        } else if (new[] {"invincible", "health", "resource", "jump", "tools", "noclip"}.Contains(key)) {
            if (value != 0 && value != 1) throw new ArgumentException("Переключатель: 0 или 1");
            if (key == "tools" && !silk) throw new ArgumentException("Инструменты доступны в Silksong");
            if (!original.ContainsKey(key)) original[key] = ReadToggle(key);
            ownedPlayer = player;
            SetToggle(key, value == 1);
        } else if (key == "damage") {
            if (value < 1 || value > 20) throw new ArgumentException("Урон: от 1 до 20×");
            if (!damageOwned) {
                damageOriginal = Float(Get(silk ? (object)mod : player, silk ? "extraNailDamage" : "nailDamage"));
                damageBase = Math.Max(1, Float(Get(player, "nailDamage")));
                damageOwned = true; ownedPlayer = player;
            }
            Set(silk ? (object)mod : player, silk ? "extraNailDamage" : "nailDamage",
                silk ? (int)Math.Round(damageOriginal + damageBase * (value - 1)) : (int)Math.Round(damageBase * value));
            Call(Find("PlayMakerFSM"), "BroadcastEvent", "UPDATE NAIL DAMAGE");
            state.damage = value;
        } else if (key == "speed") {
            if (value < .5f || value > 3) throw new ArgumentException("Скорость: от 0.5 до 3×");
            if (Bool(Call(manager, "IsGamePaused"))) throw new InvalidOperationException("Снимите игру с паузы для изменения скорости.");
            if (!speedOwned) { speedOriginal = ReadSpeed(); speedOwned = true; }
            SetSpeed(value);
        } else if (key == "currency") {
            if (value < 1 || value > 100000 || value != (int)value) throw new ArgumentException("Количество: 1–100000");
            Call(hero, "AddGeo", (int)value);
        } else if (key == "shards" && silk) {
            if (value < 1 || value > 10000 || value != (int)value) throw new ArgumentException("Количество: 1–10000");
            Call(hero, "AddShards", (int)value);
        } else throw new ArgumentException("Неизвестная команда");
    }
    float ReadSpeed() => silk ? Float(Get(silkTime, "CustomTimeScale")) : Float(Get(mod, "CurrentTimeScale"));
    void SetSpeed(float value) {
        if (silk) { Set(silkTime, "CustomTimeScale", value); return; }
        Set(mod, "CurrentTimeScale", value);
        Set(mod, "TimeScaleActive", Math.Abs(value - 1) > .01f);
        var type = Find("DebugMod.MonoBehaviours.TimeScale");
        deferredTimeRemoval = false;
        if (manager is Component gm && type != null) {
            var component = gm.GetComponent(type);
            if (Math.Abs(value - 1) > .01f && component == null) gm.gameObject.AddComponent(type);
            else if (Math.Abs(value - 1) <= .01f && component != null) {
                // Upstream OnDestroy forces timeScale=1. Dispose only after unpausing.
                if (Bool(Call(manager, "IsGamePaused"))) deferredTimeRemoval = true;
                else Destroy(component);
            }
        }
        if (manager != null && !Bool(Call(manager, "IsGamePaused"))) Time.timeScale = value;
    }
    void ResetOwned() {
        state.dash = state.fastAttack = false;
        RestoreMovement();
        foreach (var item in original.ToArray()) {
            try {
                if (item.Key == "jump" && ownedPlayer != null) Set(ownedPlayer, "infiniteAirJump", item.Value);
                else SetToggle(item.Key, item.Value);
                original.Remove(item.Key);
            } catch (Exception e) { Logger.LogWarning("Restore " + item.Key + ": " + RootMessage(e)); }
        }
        if (damageOwned) {
            Set(silk ? (object)mod : ownedPlayer, silk ? "extraNailDamage" : "nailDamage", (int)damageOriginal);
            Call(Find("PlayMakerFSM"), "BroadcastEvent", "UPDATE NAIL DAMAGE");
            damageOwned = false; state.damage = 1;
        }
        if (speedOwned) { SetSpeed(speedOriginal); speedOwned = false; }
        ownedPlayer = null;
    }
    void RestoreMovement() {
        if (movementHero is Component component && component != null)
            foreach (var item in movementOriginal) Set(movementHero, item.Key, item.Value);
        movementOriginal.Clear(); movementHero = null; state.move = 1;
    }
    void ReadState() {
        state.invincible = ReadToggle("invincible"); state.healthLock = ReadToggle("health");
        state.resource = ReadToggle("resource"); state.jump = ReadToggle("jump");
        state.tools = ReadToggle("tools"); state.noclip = ReadToggle("noclip");
        state.health = Int(Get(player, "health")); state.maxHealth = Int(Get(player, "maxHealth"));
        state.currency = Int(Get(player, "geo")); state.speed = ReadSpeed();
        state.paused = manager != null && Bool(Call(manager, "IsGamePaused"));
        state.runtimeScale = Time.timeScale;
        state.actualDamage = Int(Get(player, "nailDamage"));
        state.actualRunSpeed = hero is Component component && component != null ? Float(Get(hero, "RUN_SPEED")) : 0;
        state.shards = silk ? Int(Get(player, "ShellShards")) : 0;
    }
    void WriteState() {
        state.timestamp = Now;
        string path = Path.Combine(folder, "status.json"), temp = path + ".tmp";
        File.WriteAllText(temp, JsonUtility.ToJson(state));
        if (File.Exists(path)) File.Replace(temp, path, null); else File.Move(temp, path);
    }
    static string RootMessage(Exception e) => (e is TargetInvocationException && e.InnerException != null ? e.InnerException : e).Message;
    void OnDestroy() { try { ResetOwned(); } catch (Exception e) { Logger.LogWarning(e); } }
}
