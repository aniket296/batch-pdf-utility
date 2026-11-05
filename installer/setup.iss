; ============================================================================
; Inno Setup Script for Batch PDF Metadata & Watermarking Studio
; ============================================================================

#define MyAppName "Batch PDF Metadata & Watermarking Studio"
#define MyAppShortName "Batch PDF Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Open Source Developer"
#define MyAppURL "https://github.com/aniket296/batch-pdf-utility"
#define MyAppExeName "BatchPDFStudio.exe"

[Setup]
AppId={{8F9C3E2A-4D71-4A1E-9B65-72E1A04C5D89}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\BatchPDFStudio
DefaultGroupName={#MyAppShortName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=BatchPDFStudio_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppShortName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppShortName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

