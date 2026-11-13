if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "--steam-launch":
        from trainer.steam import run_steam_game
        raise SystemExit(run_steam_game(sys.argv[2], sys.argv[3:]))
    else:
        from trainer.app import main
        raise SystemExit(main())
