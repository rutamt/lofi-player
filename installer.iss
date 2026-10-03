; Inno Setup Script for LoFi HUD
; Compiles dist/lofi_hud into a standalone setup wizard installer (LoFiHUD_Setup.exe)

#define MyAppName "LoFi HUD"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "RutamT"
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
Source: "dist\lofi_hud\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*\tzdata\*, *\tzdata"
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up AppData config/cache directory on uninstall
Type: filesandordirs; Name: "{userappdata}\LoFiHUD"
Type: files; Name: "{userstartup}\{#MyAppName}.lnk"
Type: files; Name: "{userprograms}\{#MyAppName}.lnk"

[Code]
var
  DeleteMusicChoice: Boolean;

function InitializeUninstall(): Boolean;
var
  Form: TSetupForm;
  TitleLabel, DescLabel, SubNoteLabel: TNewStaticText;
  DeleteMusicCheckbox: TNewCheckBox;
  BtnUninstall, BtnCancel: TNewButton;
begin
  Result := False; // Default to cancel unless user clicks Uninstall
  DeleteMusicChoice := False;

  Form := CreateCustomForm(ScaleX(480), ScaleY(210), False, True);
  try
    Form.Caption := 'Uninstall LoFi HUD';
    Form.Position := poScreenCenter;
    Form.Font.Name := 'Segoe UI';

    TitleLabel := TNewStaticText.Create(Form);
    TitleLabel.Parent := Form;
    TitleLabel.Left := ScaleX(24);
    TitleLabel.Top := ScaleY(18);
    TitleLabel.Font.Name := 'Segoe UI';
    TitleLabel.Font.Size := 12;
    TitleLabel.Font.Style := [fsBold];
    TitleLabel.Caption := 'Uninstall LoFi HUD';

    DescLabel := TNewStaticText.Create(Form);
    DescLabel.Parent := Form;
    DescLabel.Left := ScaleX(24);
    DescLabel.Top := ScaleY(48);
    DescLabel.Width := Form.ClientWidth - ScaleX(48);
    DescLabel.Height := ScaleY(36);
    DescLabel.AutoSize := False;
    DescLabel.WordWrap := True;
    DescLabel.Font.Name := 'Segoe UI';
    DescLabel.Font.Size := 9;
    DescLabel.Caption := 'Are you sure you want to completely remove LoFi HUD, its shortcuts, and all application configurations from your computer?';

    DeleteMusicCheckbox := TNewCheckBox.Create(Form);
    DeleteMusicCheckbox.Parent := Form;
    DeleteMusicCheckbox.Left := ScaleX(24);
    DeleteMusicCheckbox.Top := ScaleY(96);
    DeleteMusicCheckbox.Width := Form.ClientWidth - ScaleX(48);
    DeleteMusicCheckbox.Font.Name := 'Segoe UI';
    DeleteMusicCheckbox.Font.Size := 9;
    DeleteMusicCheckbox.Caption := 'Also permanently delete my music library and downloaded songs folder';
    DeleteMusicCheckbox.Checked := False; // UNCHECKED by default!

    SubNoteLabel := TNewStaticText.Create(Form);
    SubNoteLabel.Parent := Form;
    SubNoteLabel.Left := ScaleX(44);
    SubNoteLabel.Top := ScaleY(118);
    SubNoteLabel.Width := Form.ClientWidth - ScaleX(68);
    SubNoteLabel.Font.Name := 'Segoe UI';
    SubNoteLabel.Font.Size := 8;
    SubNoteLabel.Font.Color := clGray;
    SubNoteLabel.Caption := 'Leave this unchecked to keep your music files safe on your computer.';

    BtnCancel := TNewButton.Create(Form);
    BtnCancel.Parent := Form;
    BtnCancel.Width := ScaleX(85);
    BtnCancel.Height := ScaleY(26);
    BtnCancel.Left := Form.ClientWidth - BtnCancel.Width - ScaleX(24);
    BtnCancel.Top := Form.ClientHeight - BtnCancel.Height - ScaleY(18);
    BtnCancel.Font.Name := 'Segoe UI';
    BtnCancel.Caption := 'Cancel';
    BtnCancel.ModalResult := mrCancel;
    BtnCancel.Cancel := True;

    BtnUninstall := TNewButton.Create(Form);
    BtnUninstall.Parent := Form;
    BtnUninstall.Width := ScaleX(90);
    BtnUninstall.Height := ScaleY(26);
    BtnUninstall.Left := BtnCancel.Left - BtnUninstall.Width - ScaleX(10);
    BtnUninstall.Top := BtnCancel.Top;
    BtnUninstall.Font.Name := 'Segoe UI';
    BtnUninstall.Caption := 'Uninstall';
    BtnUninstall.ModalResult := mrOk;
    BtnUninstall.Default := True;

    if Form.ShowModal() = mrOk then
    begin
      DeleteMusicChoice := DeleteMusicCheckbox.Checked;
      Result := True;
    end;
  finally
    Form.Free();
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  UninstKey, UninstPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Append /SILENT to Windows Add/Remove Programs registry so only our custom checkbox dialog displays
    UninstKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#SetupSetting("AppId")}') + '_is1';
    if RegQueryStringValue(HKCU, UninstKey, 'UninstallString', UninstPath) then
    begin
      if Pos('/SILENT', UninstPath) = 0 then
        RegWriteStringValue(HKCU, UninstKey, 'UninstallString', UninstPath + ' /SILENT');
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    if FileExists(ExpandConstant('{app}\{#MyAppExeName}')) then
    begin
      if DeleteMusicChoice then
        Exec(ExpandConstant('{app}\{#MyAppExeName}'), '--uninstall --delete-music', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
      else
        Exec(ExpandConstant('{app}\{#MyAppExeName}'), '--uninstall --keep-music', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
