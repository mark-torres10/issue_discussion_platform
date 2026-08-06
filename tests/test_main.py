def test_main_runs(capsys):
    from main import main

    main()
    captured = capsys.readouterr()
    assert "issue-discussion-platform" in captured.out
