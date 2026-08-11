Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "d:\Siva Sai\MyProjects\dbplane\dbplane"

' Run the Django server silently in background (0 = hidden, False = don't wait)
WshShell.Run "cmd /c python manage.py runserver 0.0.0.0:8000", 0, False

' Wait 3 seconds for server to start, then open browser
WScript.Sleep 3000
WshShell.Run "http://127.0.0.1:8000/", 1, False
