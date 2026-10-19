; Liha Assistant Inno Setup Installer Script
; Requires Inno Setup 6 (https://jrsoftware.org/isdl.php)

#define MyAppName "Liha Assistant"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Liha AI"
#define MyAppURL "https://github.com/liha-ai/liha"
#define MyAppExeName "LihaAssistant.exe"

[Setup]
AppId={{D38F3971-4BA2-49F1-8B35-B5E397B1A5C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=LihaAssistant-Setup-v{#MyAppVersion}
SetupIconFile=liha_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\LihaAssistant\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\LihaAssistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\liha_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\liha_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
