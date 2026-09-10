$ErrorActionPreference="Stop"
$g="D:\SteamLibrary\steamapps\common\ELDEN RING NIGHTREIGN\Game"; $o="$g\_ap_extract\dec"; New-Item -ItemType Directory -Force $o | Out-Null
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class Oodle { [DllImport("oo2core_9_win64.dll")] public static extern long OodleLZ_Decompress(byte[] src, long srcLen, byte[] dst, long dstLen, int fuzz, int crc, int verbose, IntPtr dstBase, long e, IntPtr cb, IntPtr cbCtx, IntPtr scratch, long scratchSize, int threadPhase); }
"@
$env:PATH="$g;$env:PATH"; [Environment]::CurrentDirectory=$g
function Slice($src,$off,$len){ $in=[IO.File]::OpenRead($src); $in.Seek($off,0)|Out-Null; $buf=New-Object byte[] $len; $n=0; while($n -lt $len){ $r=$in.Read($buf,$n,$len-$n); if($r -le 0){break}; $n+=$r }; $in.Close(); return ,$buf }
function HexBytes($h){ $b=New-Object byte[] ($h.Length/2); for($i=0;$i -lt $b.Length;$i++){ $b[$i]=[Convert]::ToByte($h.Substring($i*2,2),16) }; return ,$b }
function AesEcb($data,$keyhex,$ranges){ $aes=[System.Security.Cryptography.Aes]::Create(); $aes.Mode="ECB"; $aes.Padding="None"; $aes.Key=HexBytes $keyhex; $dec=$aes.CreateDecryptor()
  foreach($r in $ranges){ $s=$r[0]; $e=$r[1]; $n=$e-$s; $n=$n-($n%16); if($n -le 0){continue}; $out=$dec.TransformFinalBlock($data,$s,$n); [Array]::Copy($out,0,$data,$s,$n) } }
function BE32($b,$i){ return ([int]$b[$i] -shl 24) -bor ([int]$b[$i+1] -shl 16) -bor ([int]$b[$i+2] -shl 8) -bor [int]$b[$i+3] }
function Dcx($d){ if(-not($d[0] -eq 0x44 -and $d[1] -eq 0x43 -and $d[2] -eq 0x58)){ return ,$d }
  $unc=BE32 $d 0x1C; $comp=BE32 $d 0x20; $i=0; for($j=0;$j -lt $d.Length-4;$j++){ if($d[$j] -eq 0x44 -and $d[$j+1] -eq 0x43 -and $d[$j+2] -eq 0x41 -and $d[$j+3] -eq 0){ $i=$j; break } }
  $start=$i+(BE32 $d ($i+4)); $payload=New-Object byte[] $comp; [Array]::Copy($d,$start,$payload,0,$comp)
  $dst=New-Object byte[] ($unc+64); $n=[Oodle]::OodleLZ_Decompress($payload,$comp,$dst,$unc,1,0,0,[IntPtr]::Zero,0,[IntPtr]::Zero,[IntPtr]::Zero,[IntPtr]::Zero,0,3)
  if($n -ne $unc){ throw "oodle failed: $n vs $unc" }; $out=New-Object byte[] $unc; [Array]::Copy($dst,0,$out,0,$unc); return ,$out }
$manifest = @'
[{"path": "/event/common_func.emevd.dcx", "archive": "data0", "offset": 19593696, "size": 74384, "key": "440994ea7aebff38636fc3e13f63f623", "ranges": [[0, 74384]]}, {"path": "/msg/engus/item_dlc01.msgbnd.dcx", "archive": "data0", "offset": 4839333289, "size": 209904, "key": "e2ada2b99da3171f9a57da55f63af274", "ranges": [[0, 209904]]}, {"path": "/msg/engus/menu_dlc01.msgbnd.dcx", "archive": "data0", "offset": 4839543193, "size": 158976, "key": "e2ada2b99da3171f9a57da55f63af274", "ranges": [[0, 158976]]}, {"path": "/script/talk/m10_00_00_00.talkesdbnd.dcx", "archive": "data0", "offset": 3198327040, "size": 335760, "key": "0b49cb6c804641c1191c3d16886b6f75", "ranges": [[0, 335760]]}, {"path": "/script/talk/m00_00_00_00.talkesdbnd.dcx", "archive": "data0", "offset": 3198297424, "size": 29616, "key": "0b49cb6c804641c1191c3d16886b6f75", "ranges": [[0, 29616]]}, {"path": "/script/talk/m60_00_00_00.talkesdbnd.dcx", "archive": "data0", "offset": 3198772272, "size": 32048, "key": "0b49cb6c804641c1191c3d16886b6f75", "ranges": [[0, 32048]]}]
'@ | ConvertFrom-Json
foreach($m in $manifest){ $data=Slice "$g\$($m.archive).bdt" $m.offset $m.size; if($m.key){ AesEcb $data $m.key $m.ranges }; $out=Dcx $data
  $name=($m.path.TrimStart("/") -replace "/","__") -replace "\.dcx$",""; [IO.File]::WriteAllBytes("$o\$name",$out); Write-Host "$name -> $($out.Length) bytes" }
Write-Host "round3 done"
