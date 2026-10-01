1. Install PyInstaller
pip install pyinstaller
2. Navigate to the folder where your main.py file is located:
cd "C:\User..."
---------------------------------------------------------------------------------------------------------------------------
3. Create a standalone executable with icon
pyinstaller --onefile --windowed --name EyeGuard --icon=..\assets\media\icons\icon.ico --distpath publish --workpath publish\build --specpath publish --add-data "../assets/media/sounds;assets/media/sounds" --add-data "../assets/media/icons;assets/media/icons" --add-data "../assets/media/figures;assets/media/figures" main\main.py

4. Create a standalone executable with icon
pyinstaller --onefile --windowed --name EyeGuardConfigurator --icon=..\assets\media\icons\icon.ico --distpath publish --workpath publish\build --specpath publish --add-data "../assets/media/sounds;assets/media/sounds" --add-data "../assets/media/icons;assets/media/icons" --add-data "../assets/media/figures;assets/media/figures" main\configurator.py
---------------------------------------------------------------------------------------------------------------------------
5. Optional for removing non necessary files -> run in pycharm terminal
Get-ChildItem -Path .\publish | Where-Object {
    $_.Name -ne 'templates' -and
    $_.Name -ne 'active_config.json' -and
    $_.Extension -ne '.exe'
} | Remove-Item -Force -Recurse