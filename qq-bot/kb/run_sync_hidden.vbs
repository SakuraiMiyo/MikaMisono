' run_sync_hidden.vbs —— 计划任务入口:隐藏窗口运行日记同步(不弹任何终端框)
' 链路:wscript(本文件,窗口级0) → run_sync_hidden.bat(重定向到 diary_sync.log) → mika_kb.py --sync-diary
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\OneDrive\MikaMisono\qq-bot\kb"
sh.Run """C:\OneDrive\MikaMisono\qq-bot\kb\run_sync_hidden.bat""", 0, False
