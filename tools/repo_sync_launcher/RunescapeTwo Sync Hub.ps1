Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$RepoPath = 'C:\Users\Hesse\Desktop\Codex\runescapetwo'
$UnifiedBat = Join-Path $RepoPath 'Start Unified Vision Tester.bat'

function Invoke-Git {
    param([string[]]$Args)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'git'
    $psi.WorkingDirectory = $RepoPath
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    foreach ($arg in $Args) { [void]$psi.ArgumentList.Add($arg) }
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    [pscustomobject]@{ ExitCode = $p.ExitCode; Output = ($stdout + $stderr).Trim() }
}

function Get-RepoState {
    if (-not (Test-Path (Join-Path $RepoPath '.git'))) {
        return [pscustomobject]@{ Ok=$false; Summary='Repo niet gevonden'; Details=$RepoPath; Changed=0; Ahead=0; Behind=0 }
    }

    $status = Invoke-Git @('status','--porcelain')
    $changedLines = @($status.Output -split "`r?`n" | Where-Object { $_.Trim() })

    [void](Invoke-Git @('fetch','origin','--quiet'))
    $counts = Invoke-Git @('rev-list','--left-right','--count','HEAD...origin/main')
    $ahead = 0
    $behind = 0
    if ($counts.ExitCode -eq 0 -and $counts.Output -match '^(\d+)\s+(\d+)$') {
        $ahead = [int]$matches[1]
        $behind = [int]$matches[2]
    }

    $summary = if ($changedLines.Count -gt 0) {
        "$($changedLines.Count) lokale wijziging(en)"
    } elseif ($ahead -gt 0 -or $behind -gt 0) {
        'Git status niet gelijk'
    } else {
        'Alles is gesynchroniseerd'
    }

    [pscustomobject]@{
        Ok=$true
        Summary=$summary
        Details=($changedLines -join "`n")
        Changed=$changedLines.Count
        Ahead=$ahead
        Behind=$behind
    }
}

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="RuneScapeTwo Sync Hub" Height="620" Width="760"
        WindowStartupLocation="CenterScreen" ResizeMode="CanMinimize"
        Background="#0D1117" Foreground="#F3F4F6">
    <Window.Resources>
        <LinearGradientBrush x:Key="PanelGradient" StartPoint="0,0" EndPoint="1,1">
            <GradientStop Color="#151B28" Offset="0"/>
            <GradientStop Color="#0F1722" Offset="1"/>
        </LinearGradientBrush>
        <LinearGradientBrush x:Key="PrimaryGradient" StartPoint="0,0" EndPoint="1,0">
            <GradientStop Color="#6D5DFB" Offset="0"/>
            <GradientStop Color="#8A63F8" Offset="1"/>
        </LinearGradientBrush>
        <Style TargetType="Button">
            <Setter Property="Foreground" Value="White"/>
            <Setter Property="FontSize" Value="14"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Height" Value="46"/>
            <Setter Property="Margin" Value="0,0,0,10"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border x:Name="Border" CornerRadius="12" Background="{TemplateBinding Background}" BorderBrush="#2A3442" BorderThickness="1">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Border" Property="Opacity" Value="0.88"/></Trigger>
                            <Trigger Property="IsPressed" Value="True"><Setter TargetName="Border" Property="Opacity" Value="0.72"/></Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>
    </Window.Resources>

    <Grid Margin="24">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <StackPanel Grid.Row="0" Margin="4,0,4,18">
            <TextBlock Text="RuneScapeTwo" FontSize="30" FontWeight="Bold"/>
            <TextBlock Text="Git Sync Hub" FontSize="14" Foreground="#94A3B8" Margin="1,3,0,0"/>
        </StackPanel>

        <Border Grid.Row="1" CornerRadius="16" Background="{StaticResource PanelGradient}" BorderBrush="#263244" BorderThickness="1" Padding="18" Margin="0,0,0,16">
            <Grid>
                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <StackPanel>
                    <TextBlock x:Name="StatusTitle" Text="Status laden..." FontSize="17" FontWeight="SemiBold"/>
                    <TextBlock x:Name="StatusMeta" Text="" Foreground="#94A3B8" Margin="0,5,0,0"/>
                </StackPanel>
                <Ellipse x:Name="StatusDot" Grid.Column="1" Width="14" Height="14" Fill="#F59E0B" VerticalAlignment="Center" Margin="20,0,4,0"/>
            </Grid>
        </Border>

        <Grid Grid.Row="2">
            <Grid.ColumnDefinitions><ColumnDefinition Width="0.9*"/><ColumnDefinition Width="1.1*"/></Grid.ColumnDefinitions>

            <StackPanel Grid.Column="0" Margin="0,0,12,0">
                <Button x:Name="SyncButton" Content="Sync + Commit + Push" Background="{StaticResource PrimaryGradient}"/>
                <Button x:Name="PullButton" Content="Pull laatste GitHub" Background="#182233"/>
                <Button x:Name="TesterButton" Content="Open Unified Vision Tester" Background="#182233"/>
                <Button x:Name="FolderButton" Content="Open RuneScapeTwo map" Background="#182233"/>
                <Button x:Name="RefreshButton" Content="Refresh status" Background="#182233"/>
            </StackPanel>

            <Border Grid.Column="1" CornerRadius="16" Background="#0A0F16" BorderBrush="#263244" BorderThickness="1" Padding="14">
                <Grid>
                    <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                    <TextBlock Text="LOCAL CHANGES" FontSize="12" FontWeight="Bold" Foreground="#94A3B8" Margin="2,0,0,10"/>
                    <TextBox x:Name="ChangesBox" Grid.Row="1" IsReadOnly="True" Background="Transparent" Foreground="#D7DEE8" BorderThickness="0" FontFamily="Consolas" FontSize="12" TextWrapping="NoWrap" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto"/>
                </Grid>
            </Border>
        </Grid>

        <TextBlock Grid.Row="3" x:Name="Footer" Text="Repo: C:\Users\Hesse\Desktop\Codex\runescapetwo" Foreground="#667085" FontSize="11" Margin="4,14,4,0"/>
    </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

$StatusTitle = $window.FindName('StatusTitle')
$StatusMeta = $window.FindName('StatusMeta')
$StatusDot = $window.FindName('StatusDot')
$ChangesBox = $window.FindName('ChangesBox')
$SyncButton = $window.FindName('SyncButton')
$PullButton = $window.FindName('PullButton')
$TesterButton = $window.FindName('TesterButton')
$FolderButton = $window.FindName('FolderButton')
$RefreshButton = $window.FindName('RefreshButton')

function Set-Busy([bool]$Busy) {
    $SyncButton.IsEnabled = -not $Busy
    $PullButton.IsEnabled = -not $Busy
    $RefreshButton.IsEnabled = -not $Busy
}

function Refresh-Ui {
    $state = Get-RepoState
    $StatusTitle.Text = $state.Summary
    $StatusMeta.Text = "Local: $($state.Changed)   Ahead: $($state.Ahead)   Behind: $($state.Behind)"
    $ChangesBox.Text = if ($state.Details) { $state.Details } else { 'Geen lokale wijzigingen.' }

    if (-not $state.Ok) {
        $StatusDot.Fill = '#EF4444'
    } elseif ($state.Changed -eq 0 -and $state.Ahead -eq 0 -and $state.Behind -eq 0) {
        $StatusDot.Fill = '#22C55E'
    } else {
        $StatusDot.Fill = '#F59E0B'
    }
}

$RefreshButton.Add_Click({ Refresh-Ui })

$FolderButton.Add_Click({
    if (Test-Path $RepoPath) { Start-Process explorer.exe $RepoPath }
})

$TesterButton.Add_Click({
    if (Test-Path $UnifiedBat) { Start-Process -FilePath $UnifiedBat -WorkingDirectory $RepoPath }
})

$PullButton.Add_Click({
    Set-Busy $true
    try {
        $status = Invoke-Git @('status','--porcelain')
        if ($status.Output.Trim()) {
            [System.Windows.MessageBox]::Show('Er staan lokale wijzigingen. Gebruik Sync + Commit + Push zodat niets verloren gaat.','Pull geblokkeerd') | Out-Null
            return
        }
        $pull = Invoke-Git @('pull','--ff-only','origin','main')
        if ($pull.ExitCode -ne 0) {
            [System.Windows.MessageBox]::Show($pull.Output,'Pull mislukt') | Out-Null
        }
    } finally {
        Set-Busy $false
        Refresh-Ui
    }
})

$SyncButton.Add_Click({
    Set-Busy $true
    try {
        $status = Invoke-Git @('status','--porcelain')
        if ($status.Output.Trim()) {
            $add = Invoke-Git @('add','-A')
            if ($add.ExitCode -ne 0) { throw $add.Output }

            $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
            $commit = Invoke-Git @('commit','-m',"Local sync $stamp")
            if ($commit.ExitCode -ne 0 -and $commit.Output -notmatch 'nothing to commit') { throw $commit.Output }
        }

        $fetch = Invoke-Git @('fetch','origin')
        if ($fetch.ExitCode -ne 0) { throw $fetch.Output }

        $rebase = Invoke-Git @('rebase','origin/main')
        if ($rebase.ExitCode -ne 0) {
            [System.Windows.MessageBox]::Show("Sync gestopt vanwege een conflict.`n`n$($rebase.Output)`n`nEr is niets geforceerd of overschreven.",'Conflict gevonden') | Out-Null
            return
        }

        $push = Invoke-Git @('push','origin','main')
        if ($push.ExitCode -ne 0) { throw $push.Output }

        [System.Windows.MessageBox]::Show('Alles staat gelijk. Lokale wijzigingen zijn gecommit, GitHub is bijgewerkt en main is gepusht.','Sync klaar') | Out-Null
    } catch {
        [System.Windows.MessageBox]::Show($_.Exception.Message,'Sync mislukt') | Out-Null
    } finally {
        Set-Busy $false
        Refresh-Ui
    }
})

$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(4)
$timer.Add_Tick({ Refresh-Ui })
$timer.Start()

Refresh-Ui
[void]$window.ShowDialog()
