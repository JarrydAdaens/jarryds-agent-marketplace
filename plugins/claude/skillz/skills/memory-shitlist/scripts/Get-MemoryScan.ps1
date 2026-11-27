# Scans the running processes and groups them into apps. Read-only: it changes nothing.
#
# Output:
#   - Writes the full scan as JSON to -OutFile (default: a new file under %TEMP%\memory-scan).
#   - Prints a compact summary: a SYSTEM line, a SCAN_FILE line, a CHROMIUM line with the
#     memory of all Chromium-based groups, then one GROUP line for each group whose own memory
#     is at least -MinMB (only Chromium-based groups with -ChromiumOnly).
#
# Grouping rules:
#   - A process joins its parent's group when both executables are in the same folder, or the
#     child's folder is inside the parent's folder (Chromium and Electron helper processes).
#   - Console helpers (conhost, OpenConsole, crashpad_handler) join their parent's group.
#   - WebView2 processes (msedgewebview2) join the group of the app that hosts them.
#   - Any other process starts a new group. Its parent's group becomes its parentGroup.
#
# Kinds (first match wins): Electron, Browser, CEF, WebView2, Chromium, Native.
# Memory is the working set. Shared pages count once for each process, so the sum of a
# group is larger than the memory that stopping the group gives back.

[CmdletBinding()]
param(
	[int]$MinMB = 20,
	[string]$OutFile,
	# Print only the groups that run a Chromium engine. The scan file still has every group.
	[switch]$ChromiumOnly
)

$ErrorActionPreference = 'Stop'

$consoleHelperNames = @('conhost.exe', 'openconsole.exe', 'crashpad_handler.exe')
$browserNames = @('chrome.exe', 'msedge.exe', 'brave.exe', 'vivaldi.exe', 'opera.exe', 'opera_gx.exe', 'arc.exe', 'thorium.exe', 'chromium.exe', 'yandex.exe')
$shellNames = @('powershell.exe', 'pwsh.exe', 'cmd.exe', 'bash.exe', 'wsl.exe', 'nu.exe')
$windowsDirectory = $env:windir.TrimEnd('\') + '\'
# Core Windows and security processes. Without admin rights their path is often hidden, so the
# path test alone does not find them.
$windowsCoreNames = @('system', 'registry', 'memory compression', 'secure system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'lsaiso.exe', 'svchost.exe', 'dwm.exe', 'fontdrvhost.exe', 'audiodg.exe', 'ctfmon.exe', 'sihost.exe', 'tabtip.exe', 'msmpeng.exe', 'nissrv.exe', 'securityhealthservice.exe', 'mpdefendercoreservice.exe', 'searchindexer.exe', 'spoolsv.exe', 'wudfhost.exe', 'dashost.exe', 'wmiprvse.exe', 'msedgewebview2.exe')

function Get-DirectoryOf([string]$path) {
	if ([string]::IsNullOrEmpty($path)) { return $null }
	return [System.IO.Path]::GetDirectoryName($path).TrimEnd('\') + '\'
}

function Test-HasFile([string]$directory, [string]$relativePath) {
	return Test-Path -LiteralPath (Join-Path $directory $relativePath)
}

# An Electron app ships its code in resources\app.asar or resources\app, and the V8 snapshot
# without the DLL of a browser or of CEF. Some apps (VS Code) keep these files in a
# versioned subfolder next to the executable, so the subfolders are checked too.
function Test-ElectronFolder([string]$directory) {
	$candidates = @($directory)
	$candidates += @(Get-ChildItem -LiteralPath $directory -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
	foreach ($candidate in $candidates) {
		if ((Test-HasFile $candidate 'resources\app.asar') -or (Test-HasFile $candidate 'resources\default_app.asar')) { return $true }
		$hasSnapshot = Test-HasFile $candidate 'v8_context_snapshot.bin'
		$isOtherChromium = (Test-HasFile $candidate 'chrome.dll') -or (Test-HasFile $candidate 'msedge.dll') -or (Test-HasFile $candidate 'libcef.dll')
		if ($hasSnapshot -and -not $isOtherChromium -and (Test-HasFile $candidate 'resources\app\package.json')) { return $true }
	}
	return $false
}

function Test-SameAppFolder($child, $parent) {
	if (-not $child.Directory -or -not $parent.Directory) {
		return ($null -eq $child.Directory -and $null -eq $parent.Directory -and $child.Name -eq $parent.Name)
	}
	return $child.Directory.StartsWith($parent.Directory, [StringComparison]::OrdinalIgnoreCase)
}

# Collect the processes.
$privateBytesById = @{}
foreach ($p in Get-Process) { $privateBytesById[$p.Id] = $p.PrivateMemorySize64 }

$processes = @{}
foreach ($c in Get-CimInstance Win32_Process) {
	$processes[[int]$c.ProcessId] = [pscustomobject]@{
		Id          = [int]$c.ProcessId
		ParentId    = [int]$c.ParentProcessId
		Name        = $c.Name
		NameLower   = $c.Name.ToLowerInvariant()
		Path        = $c.ExecutablePath
		Directory   = Get-DirectoryOf $c.ExecutablePath
		CommandLine = [string]$c.CommandLine
		Created     = $c.CreationDate
		WorkingSet  = [int64]$c.WorkingSetSize
		Private     = [int64]$privateBytesById[[int]$c.ProcessId]
	}
}

# A parent id is valid only if that process started before the child. Windows reuses ids.
function Get-ValidParent($process) {
	if ($process.ParentId -eq $process.Id) { return $null }
	$parent = $processes[$process.ParentId]
	if (-not $parent) { return $null }
	if ($parent.Created -and $process.Created -and $parent.Created -gt $process.Created) { return $null }
	return $parent
}

# Assign each process to a group root.
$rootById = @{}
$webViewRootIds = @{}
function Get-GroupRoot($process) {
	if ($rootById.ContainsKey($process.Id)) { return $rootById[$process.Id] }
	$rootById[$process.Id] = $process.Id  # guards against cycles
	$parent = Get-ValidParent $process
	$root = $process.Id
	if ($parent) {
		if ($process.NameLower -eq 'msedgewebview2.exe') {
			$hostProcess = $parent
			while ($hostProcess -and $hostProcess.NameLower -eq 'msedgewebview2.exe') { $hostProcess = Get-ValidParent $hostProcess }
			if ($hostProcess) {
				$root = Get-GroupRoot $hostProcess
				$webViewRootIds[$root] = $true
			}
		}
		elseif ($consoleHelperNames -contains $process.NameLower -or (Test-SameAppFolder $process $parent)) {
			$root = Get-GroupRoot $parent
		}
	}
	$rootById[$process.Id] = $root
	return $root
}
foreach ($process in $processes.Values) { [void](Get-GroupRoot $process) }

# Find this session: the nearest ancestor that is Claude Code, its descendants, and the
# terminal shell that started it.
$sessionIds = @{}
$walker = $processes[$PID]
$claude = $null
while ($walker) {
	if ($walker.NameLower -eq 'claude.exe' -or ($walker.NameLower -eq 'node.exe' -and $walker.CommandLine -match 'claude')) { $claude = $walker; break }
	$walker = Get-ValidParent $walker
}
if ($claude) {
	$sessionIds[$claude.Id] = $true
	$changed = $true
	while ($changed) {
		$changed = $false
		foreach ($process in $processes.Values) {
			if (-not $sessionIds.ContainsKey($process.Id) -and $sessionIds.ContainsKey($process.ParentId) -and (Get-ValidParent $process)) {
				$sessionIds[$process.Id] = $true
				$changed = $true
			}
		}
	}
	$shell = Get-ValidParent $claude
	if ($shell -and $shellNames -contains $shell.NameLower) { $sessionIds[$shell.Id] = $true }
}

# Build the groups.
$groupsByRoot = @{}
foreach ($process in $processes.Values) {
	$rootId = $rootById[$process.Id]
	if (-not $groupsByRoot.ContainsKey($rootId)) { $groupsByRoot[$rootId] = New-Object System.Collections.ArrayList }
	[void]$groupsByRoot[$rootId].Add($process)
}

$groups = foreach ($rootId in $groupsByRoot.Keys) {
	$members = $groupsByRoot[$rootId]
	$root = $processes[$rootId]
	$ownBytes = ($members | Measure-Object WorkingSet -Sum).Sum
	$privateBytes = ($members | Measure-Object Private -Sum).Sum
	$rendererCount = @($members | Where-Object { $_.CommandLine -match '--type=renderer' }).Count
	$hasChromiumHelpers = @($members | Where-Object { $_.CommandLine -match '--type=(renderer|gpu-process|utility)' }).Count -gt 0

	$kind = 'Native'
	$inWindowsFolder = $root.Directory -and $root.Directory.StartsWith($windowsDirectory, [StringComparison]::OrdinalIgnoreCase)
	if ($root.Directory -and -not $inWindowsFolder -and (Test-ElectronFolder $root.Directory)) { $kind = 'Electron' }
	elseif ($browserNames -contains $root.NameLower -or ($root.Directory -and ((Test-HasFile $root.Directory 'chrome.dll') -or (Test-HasFile $root.Directory 'msedge.dll')))) { $kind = 'Browser' }
	elseif ($root.Directory -and (Test-HasFile $root.Directory 'libcef.dll')) { $kind = 'CEF' }
	elseif ($webViewRootIds.ContainsKey($rootId)) { $kind = 'WebView2' }
	elseif ($hasChromiumHelpers) { $kind = 'Chromium' }

	$description = $null
	$company = $null
	if ($root.Path) {
		try {
			$info = (Get-Item -LiteralPath $root.Path).VersionInfo
			$description = $info.FileDescription
			$company = $info.CompanyName
		} catch { }
	}

	$parent = Get-ValidParent $root
	# A terminal shell is a user's tab, not part of Windows, although it runs from the Windows folder.
	$isShell = $shellNames -contains $root.NameLower
	$isWindows = (-not $isShell) -and (($root.Path -and $root.Path.StartsWith($windowsDirectory, [StringComparison]::OrdinalIgnoreCase)) -or $root.Id -le 4 -or $windowsCoreNames -contains $root.NameLower)
	$command = ($root.CommandLine -replace '\s+', ' ').Trim()
	if ($command.Length -gt 200) { $command = $command.Substring(0, 200) }

	[pscustomobject]@{
		rootPid         = $root.Id
		name            = $root.Name
		description     = $description
		company         = $company
		kind            = $kind
		chromium        = ($kind -ne 'Native')
		ownMB           = [math]::Round($ownBytes / 1MB)
		privateMB       = [math]::Round($privateBytes / 1MB)
		treeMB          = 0
		processCount    = $members.Count
		rendererCount   = $rendererCount
		pids            = @($members | Sort-Object Id | ForEach-Object { $_.Id })
		members         = @($members | Sort-Object Id | ForEach-Object { [pscustomobject]@{ pid = $_.Id; name = $_.Name; started = if ($_.Created) { $_.Created.ToString('o') } else { $null } } })
		processes       = @($members | Group-Object Name | Sort-Object Count -Descending | ForEach-Object { "$($_.Name) x$($_.Count)" })
		startedAt       = if ($root.Created) { $root.Created.ToString('yyyy-MM-dd HH:mm') } else { $null }
		parentRootPid   = if ($parent) { $rootById[$parent.Id] } else { $null }
		parentName      = if ($parent) { $parent.Name } else { $null }
		windows         = [bool]$isWindows
		shell           = [bool]$isShell
		pathHidden      = (-not $root.Path)
		service         = ($parent -and $parent.NameLower -eq 'services.exe')
		currentSession  = (@($members | Where-Object { $sessionIds.ContainsKey($_.Id) }).Count -gt 0)
		path            = $root.Path
		commandLine     = $command
		id              = $null
	}
}

# treeMB: own memory plus the memory of every group below it.
$groupByRoot = @{}
foreach ($g in $groups) { $groupByRoot[$g.rootPid] = $g }
function Get-TreeMB($group, $seen) {
	if ($seen.ContainsKey($group.rootPid)) { return 0 }
	$seen[$group.rootPid] = $true
	$total = $group.ownMB
	foreach ($child in $groups) {
		if ($child.parentRootPid -eq $group.rootPid -and $child.rootPid -ne $group.rootPid) { $total += Get-TreeMB $child $seen }
	}
	return $total
}
foreach ($g in $groups) { $g.treeMB = Get-TreeMB $g @{} }

$groups = @($groups | Sort-Object ownMB -Descending)
$index = 1
foreach ($g in $groups) { $g.id = "g$index"; $index++ }
$idByRoot = @{}
foreach ($g in $groups) { $idByRoot[$g.rootPid] = $g.id }

$os = Get-CimInstance Win32_OperatingSystem
$totalMB = [math]::Round($os.TotalVisibleMemorySize / 1KB)
$freeMB = [math]::Round($os.FreePhysicalMemory / 1KB)
$scan = [pscustomobject]@{
	scannedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
	computer  = $env:COMPUTERNAME
	totalMB   = $totalMB
	freeMB    = $freeMB
	usedMB    = $totalMB - $freeMB
	groups    = $groups
}

if (-not $OutFile) {
	$folder = Join-Path $env:TEMP 'memory-scan'
	New-Item -ItemType Directory -Force -Path $folder | Out-Null
	$OutFile = Join-Path $folder ("scan-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$scan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutFile -Encoding UTF8

"SYSTEM total={0}MB free={1}MB used={2}MB scanned={3}" -f $totalMB, $freeMB, ($totalMB - $freeMB), $scan.scannedAt
"SCAN_FILE=$OutFile"
$chromiumMB = ($groups | Where-Object { $_.chromium } | Measure-Object ownMB -Sum).Sum
if (-not $chromiumMB) { $chromiumMB = 0 }
"CHROMIUM total={0}MB groups={1}" -f $chromiumMB, @($groups | Where-Object { $_.chromium }).Count
foreach ($g in $groups | Where-Object { $_.ownMB -ge $MinMB -and ($_.chromium -or -not $ChromiumOnly) }) {
	$flags = @()
	if ($g.windows) { $flags += 'windows' }
	if ($g.service) { $flags += 'service' }
	if ($g.shell) { $flags += 'shell' }
	if ($g.pathHidden) { $flags += 'path-hidden' }
	if ($g.currentSession) { $flags += 'current-session' }
	$parentId = if ($g.parentRootPid -and $idByRoot.ContainsKey($g.parentRootPid)) { $idByRoot[$g.parentRootPid] } else { '-' }
	"GROUP {0} | own={1}MB tree={2}MB private={3}MB | kind={4} renderers={5} | procs={6} [{7}] | root={8} {9} | desc={10} | since={11} | parent={12} ({13}) | flags={14}" -f `
		$g.id, $g.ownMB, $g.treeMB, $g.privateMB, $g.kind, $g.rendererCount, $g.processCount, ($g.processes -join ', '), $g.rootPid, $g.name, $g.description, $g.startedAt, $parentId, $g.parentName, ($flags -join ',')
}
