//using Microsoft.AspNetCore.Authorization;
//using Microsoft.AspNetCore.Mvc;
//using Microsoft.AspNetCore.Mvc.RazorPages;
//using MinutAI.web.Data;
//using MinutAI.web.Models;
//using System.Diagnostics;
//using System.Text;

//namespace MinutAI.web.Pages
//{
//    [Authorize]
//    [RequestSizeLimit(300 * 1024 * 1024)]
//    public class IndexModel : PageModel
//    {
//        private readonly ApplicationDbContext _db;

//        public IndexModel(ApplicationDbContext db)
//        {
//            _db = db;
//        }

//        [BindProperty]
//        public string? ConsentConfirmed { get; set; }

//        [BindProperty]
//        public IFormFile? AudioFile { get; set; }

//        public string? StatusMessage { get; set; }

//        public void OnGet() { }

//        public async Task<IActionResult> OnPostAsync()
//        {
//            if (AudioFile == null || AudioFile.Length == 0)
//            {
//                StatusMessage = "Please upload an audio file.";
//                return Page();
//            }

//            bool consent = ConsentConfirmed == "true" || ConsentConfirmed == "on";
//            if (!consent)
//            {
//                StatusMessage = "Please confirm meeting consent before processing.";
//                return Page();
//            }

//            string? tempAudioPath = null;

//            try
//            {
//                var projectRoot = FindProjectRoot();

//                var backendDir = Path.Combine(projectRoot, "backend");
//                var outputsDir = Path.Combine(projectRoot, "outputs");
//                Directory.CreateDirectory(outputsDir);

//                // IMPORTANT: venv is inside /backend/venv
//                var pythonExe = Path.Combine(backendDir, "venv", "Scripts", "python.exe");
//                if (!System.IO.File.Exists(pythonExe))
//                    throw new FileNotFoundException($"Python venv not found at: {pythonExe}");

//                // Save upload to TEMP (avoid keeping duplicate audio in project folders)
//                var ext = Path.GetExtension(AudioFile.FileName);
//                if (string.IsNullOrWhiteSpace(ext)) ext = ".m4a";

//                var tempName = $"minutai_upload_{Guid.NewGuid():N}{ext}";
//                tempAudioPath = Path.Combine(Path.GetTempPath(), tempName);

//                await using (var stream = new FileStream(tempAudioPath, FileMode.Create, FileAccess.Write, FileShare.Read))
//                {
//                    await AudioFile.CopyToAsync(stream);
//                }

//                StatusMessage = "Processing: transcription + summary + tasks...";
//                await RunPythonAsync(
//                    pythonExe,
//                    Path.Combine(backendDir, "pipeline.py"),
//                    backendDir,
//                    $"\"{tempAudioPath}\""
//                );

//                // Read outputs
//                var transcriptPath = Path.Combine(outputsDir, "transcript.txt");
//                var summaryPath = Path.Combine(outputsDir, "summary.txt");
//                var actionsPath = Path.Combine(outputsDir, "action_items.txt");

//                var transcript = System.IO.File.Exists(transcriptPath) ? System.IO.File.ReadAllText(transcriptPath) : "";
//                var summary = System.IO.File.Exists(summaryPath) ? System.IO.File.ReadAllText(summaryPath) : "";
//                var actions = System.IO.File.Exists(actionsPath) ? System.IO.File.ReadAllText(actionsPath) : "";

//                // Save to DB + redirect to results page
//                var userEmail = User.Identity?.Name ?? "unknown";

//                // Store the original filename for display/history (audio is NOT stored on disk)
//                var record = new MeetingRecord
//                {
//                    UserEmail = userEmail,
//                    AudioFileName = AudioFile.FileName,
//                    Transcript = transcript,
//                    Summary = summary,
//                    ActionItems = actions
//                };

//                _db.Meetings.Add(record);
//                await _db.SaveChangesAsync();

//                return RedirectToPage("/Meetings/Result", new { id = record.Id });
//            }
//            catch (Exception ex)
//            {
//                StatusMessage = $"Processing failed: {ex.Message}";
//                return Page();
//            }
//            finally
//            {
//                // Always delete temp audio file to avoid duplicates filling disk
//                if (!string.IsNullOrWhiteSpace(tempAudioPath) && System.IO.File.Exists(tempAudioPath))
//                {
//                    try { System.IO.File.Delete(tempAudioPath); } catch { }
//                }
//            }
//        }

//        private string FindProjectRoot()
//        {
//            var dir = new DirectoryInfo(AppContext.BaseDirectory);

//            while (dir != null)
//            {
//                bool hasBackend = Directory.Exists(Path.Combine(dir.FullName, "backend"));
//                if (hasBackend)
//                    return dir.FullName;

//                dir = dir.Parent;
//            }

//            throw new Exception("Project root not found. Could not locate 'backend' folder.");
//        }

//        private async Task RunPythonAsync(string pythonExe, string scriptPath, string workingDir, string extraArgs)
//        {
//            var stdOutBuilder = new StringBuilder();
//            var stdErrBuilder = new StringBuilder();

//            var psi = new ProcessStartInfo
//            {
//                FileName = pythonExe,
//                Arguments = $"\"{scriptPath}\" {extraArgs}",
//                WorkingDirectory = workingDir,
//                RedirectStandardOutput = true,
//                RedirectStandardError = true,
//                UseShellExecute = false,
//                CreateNoWindow = true
//            };

//            using var process = Process.Start(psi);
//            if (process == null)
//                throw new Exception("Failed to start Python process.");

//            process.OutputDataReceived += (_, args) =>
//            {
//                if (args.Data != null) stdOutBuilder.AppendLine(args.Data);
//            };
//            process.ErrorDataReceived += (_, args) =>
//            {
//                if (args.Data != null) stdErrBuilder.AppendLine(args.Data);
//            };

//            process.BeginOutputReadLine();
//            process.BeginErrorReadLine();

//            var timeoutTask = Task.Delay(TimeSpan.FromMinutes(15));
//            var exitTask = process.WaitForExitAsync();
//            var completedTask = await Task.WhenAny(exitTask, timeoutTask);

//            if (completedTask == timeoutTask)
//            {
//                try { process.Kill(true); } catch { }
//                throw new Exception("Python process timed out.");
//            }

//            await exitTask;

//            if (process.ExitCode != 0)
//            {
//                throw new Exception(
//                    $"Python script failed:\n{scriptPath}\n\nSTDERR:\n{stdErrBuilder}\n\nSTDOUT:\n{stdOutBuilder}"
//                );
//            }
//        }
//    }
//}







using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using MinutAI.web.Data;
using MinutAI.web.Models;
using System.Diagnostics;
using System.Text;

namespace MinutAI.web.Pages
{
    [Authorize]
    [RequestSizeLimit(300 * 1024 * 1024)]
    public class IndexModel : PageModel
    {
        private readonly ApplicationDbContext _db;

        public IndexModel(ApplicationDbContext db)
        {
            _db = db;
        }

        [BindProperty]
        public string? ConsentConfirmed { get; set; }

        [BindProperty]
        public IFormFile? AudioFile { get; set; }

        public string? StatusMessage { get; set; }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (AudioFile == null || AudioFile.Length == 0)
            {
                StatusMessage = "Please upload an audio file.";
                return Page();
            }

            bool consent = ConsentConfirmed == "true" || ConsentConfirmed == "on";
            if (!consent)
            {
                StatusMessage = "Please confirm meeting consent before processing.";
                return Page();
            }

            string? tempAudioPath = null;

            try
            {
                var projectRoot = FindProjectRoot();

                var backendDir = Path.Combine(projectRoot, "backend");
                var outputsDir = Path.Combine(projectRoot, "outputs");
                Directory.CreateDirectory(outputsDir);

                // IMPORTANT: venv is inside /backend/venv
                var pythonExe = Path.Combine(backendDir, "venv", "Scripts", "python.exe");
                if (!System.IO.File.Exists(pythonExe))
                    throw new FileNotFoundException($"Python venv not found at: {pythonExe}");

                // Save upload to TEMP (avoid keeping duplicates in your project folders)
                var ext = Path.GetExtension(AudioFile.FileName);
                if (string.IsNullOrWhiteSpace(ext)) ext = ".m4a";

                var tempName = $"minutai_upload_{Guid.NewGuid():N}{ext}";
                tempAudioPath = Path.Combine(Path.GetTempPath(), tempName);

                await using (var stream = new FileStream(tempAudioPath, FileMode.Create, FileAccess.Write, FileShare.Read))
                {
                    await AudioFile.CopyToAsync(stream);
                }

                // Enforce 90-minute max duration
                var durationSeconds = await GetAudioDurationSecondsAsync(tempAudioPath);
                if (durationSeconds > 90 * 60)
                {
                    StatusMessage = $"Audio is too long ({Math.Round(durationSeconds / 60, 1)} minutes). Max allowed is 90 minutes.";
                    return Page();
                }

                StatusMessage = "Processing: transcription + summary + tasks...";
                await RunPythonAsync(
                    pythonExe,
                    Path.Combine(backendDir, "pipeline.py"),
                    backendDir,
                    $"\"{tempAudioPath}\""
                );

                // Read outputs
                var transcriptPath = Path.Combine(outputsDir, "transcript.txt");
                var summaryPath = Path.Combine(outputsDir, "summary.txt");
                var actionsPath = Path.Combine(outputsDir, "action_items.txt");

                var transcript = System.IO.File.Exists(transcriptPath) ? System.IO.File.ReadAllText(transcriptPath) : "";
                var summary = System.IO.File.Exists(summaryPath) ? System.IO.File.ReadAllText(summaryPath) : "";
                var actions = System.IO.File.Exists(actionsPath) ? System.IO.File.ReadAllText(actionsPath) : "";

                // Save to DB + redirect to results page
                var userEmail = User.Identity?.Name ?? "unknown";

                // Store original filename for history display (audio is NOT stored on disk)
                var record = new MeetingRecord
                {
                    UserEmail = userEmail,
                    AudioFileName = AudioFile.FileName,
                    Transcript = transcript,
                    Summary = summary,
                    ActionItems = actions
                };

                _db.Meetings.Add(record);
                await _db.SaveChangesAsync();

                return RedirectToPage("/Meetings/Result", new { id = record.Id });
            }
            catch (Exception ex)
            {
                StatusMessage = $"Processing failed: {ex.Message}";
                return Page();
            }
            finally
            {
                // Always delete temp upload so we don't keep duplicates
                if (!string.IsNullOrWhiteSpace(tempAudioPath) && System.IO.File.Exists(tempAudioPath))
                {
                    try { System.IO.File.Delete(tempAudioPath); } catch { }
                }
            }
        }

        private string FindProjectRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);

            while (dir != null)
            {
                bool hasBackend = Directory.Exists(Path.Combine(dir.FullName, "backend"));
                if (hasBackend)
                    return dir.FullName;

                dir = dir.Parent;
            }

            throw new Exception("Project root not found. Could not locate 'backend' folder.");
        }

        private async Task<double> GetAudioDurationSecondsAsync(string filePath)
        {
            // Requires ffprobe in PATH (usually comes with ffmpeg)
            var psi = new ProcessStartInfo
            {
                FileName = "ffprobe",
                Arguments = $"-v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{filePath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var proc = Process.Start(psi);
            if (proc == null)
                throw new Exception("Failed to start ffprobe.");

            string stdout = await proc.StandardOutput.ReadToEndAsync();
            string stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();

            if (proc.ExitCode != 0)
                throw new Exception($"ffprobe failed: {stderr}");

            if (!double.TryParse(stdout.Trim(), System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out var seconds))
                throw new Exception("Could not parse audio duration.");

            return seconds;
        }

        private async Task RunPythonAsync(string pythonExe, string scriptPath, string workingDir, string extraArgs)
        {
            var stdOutBuilder = new StringBuilder();
            var stdErrBuilder = new StringBuilder();

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{scriptPath}\" {extraArgs}",
                WorkingDirectory = workingDir,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(psi);
            if (process == null)
                throw new Exception("Failed to start Python process.");

            process.OutputDataReceived += (_, args) =>
            {
                if (args.Data != null) stdOutBuilder.AppendLine(args.Data);
            };
            process.ErrorDataReceived += (_, args) =>
            {
                if (args.Data != null) stdErrBuilder.AppendLine(args.Data);
            };

            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            var timeoutTask = Task.Delay(TimeSpan.FromMinutes(15));
            var exitTask = process.WaitForExitAsync();
            var completedTask = await Task.WhenAny(exitTask, timeoutTask);

            if (completedTask == timeoutTask)
            {
                try { process.Kill(true); } catch { }
                throw new Exception("Python process timed out.");
            }

            await exitTask;

            if (process.ExitCode != 0)
            {
                throw new Exception(
                    $"Python script failed:\n{scriptPath}\n\nSTDERR:\n{stdErrBuilder}\n\nSTDOUT:\n{stdOutBuilder}"
                );
            }
        }
    }
}