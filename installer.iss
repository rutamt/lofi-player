; Inno Setup Script for LoFi HUD
; Compiles dist/lofi_hud into a standalone setup wizard installer (LoFiHUD_Setup.exe)

#define MyAppName "LoFi HUD"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Rutam"
#define MyAppExeName "lofi_hud.exe"

[Setup]
AppId={{D37F8E8B-6E35-4E4A-B6A9-417A2FA73F12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userpf}\{#MyAppName}
DisableProgramGroupPage=yes
; Per-user install: no Administrator / UAC prompt required
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=LoFiHUD_Setup_v{#MyAppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=onboarding.txt

; Close any running instance of LoFi HUD before installing / upgrading
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\lofi_hud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Clean up shortcuts, startup entries, and AppData config before deleting app files
Filename: "{app}\{#MyAppExeName}"; Parameters: "--uninstall"; Flags: waituntilterminated skipifdoesntexist

[UninstallDelete]
; Clean up AppData config/cache directory on uninstall
Type: filesandordirs; Name: "{userappdata}\LoFiHUD"
Type: files; Name: "{userstartup}\{#MyAppName}.lnk"
Type: files; Name: "{userprograms}\{#MyAppName}.lnk"
