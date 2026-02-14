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

            try
            {
                var projectRoot = FindProjectRoot();

                var testAudioDir = Path.Combine(projectRoot, "test_audio");
                var outputsDir = Path.Combine(projectRoot, "outputs");
                var backendDir = Path.Combine(projectRoot, "backend");

                Directory.CreateDirectory(testAudioDir);
                Directory.CreateDirectory(outputsDir);

                var pythonExe = Path.Combine(projectRoot, "venv", "Scripts", "python.exe");
                if (!System.IO.File.Exists(pythonExe))
                    throw new FileNotFoundException($"Python venv not found at: {pythonExe}");

                // Save upload with unique name
                var ext = Path.GetExtension(AudioFile.FileName);
                if (string.IsNullOrWhiteSpace(ext)) ext = ".m4a";

                var uniqueFileName = $"meeting_{DateTime.Now:yyyyMMdd_HHmmss}{ext}";
                var uploadedAudioPath = Path.Combine(testAudioDir, uniqueFileName);

                await using (var stream = new FileStream(uploadedAudioPath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite))
                {
                    await AudioFile.CopyToAsync(stream);
                }

                // Run pipeline
                StatusMessage = "Step 1/4: Transcribing audio (Whisper)...";
                await RunPythonAsync(pythonExe, Path.Combine(backendDir, "whisper_test.py"), projectRoot, $"\"{uploadedAudioPath}\"");

                await Task.Delay(300);

                StatusMessage = "Step 2/4: Cleaning transcript...";
                await RunPythonAsync(pythonExe, Path.Combine(backendDir, "text_cleaner.py"), projectRoot, "");

                StatusMessage = "Step 3/4: Generating summary...";
                await RunPythonAsync(pythonExe, Path.Combine(backendDir, "summariser.py"), projectRoot, "");

                StatusMessage = "Step 4/4: Extracting action items...";
                await RunPythonAsync(pythonExe, Path.Combine(backendDir, "action_extractor.py"), projectRoot, "");

                // Read outputs
                var transcriptPath = Path.Combine(outputsDir, "transcript.txt");
                var summaryPath = Path.Combine(outputsDir, "summary.txt");
                var actionsPath = Path.Combine(outputsDir, "action_items.txt");

                var transcript = System.IO.File.Exists(transcriptPath) ? System.IO.File.ReadAllText(transcriptPath) : "";
                var summary = System.IO.File.Exists(summaryPath) ? System.IO.File.ReadAllText(summaryPath) : "";
                var actions = System.IO.File.Exists(actionsPath) ? System.IO.File.ReadAllText(actionsPath) : "";

                // Save to DB + redirect to results page
                var userEmail = User.Identity?.Name ?? "unknown";

                var record = new MeetingRecord
                {
                    UserEmail = userEmail,
                    AudioFileName = uniqueFileName,
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
                // Show friendly message on upload page instead of crashing the app
                StatusMessage = $"Processing failed: {ex.Message}";
                return Page();
            }
        }

        private string FindProjectRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);

            while (dir != null)
            {
                bool hasBackend = Directory.Exists(Path.Combine(dir.FullName, "backend"));
                bool hasVenv = Directory.Exists(Path.Combine(dir.FullName, "venv"));

                if (hasBackend && hasVenv)
                    return dir.FullName;

                dir = dir.Parent;
            }

            throw new Exception("Project root not found. Could not locate 'backend' and 'venv' folders.");
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

            process.OutputDataReceived += (_, args) => { if (args.Data != null) stdOutBuilder.AppendLine(args.Data); };
            process.ErrorDataReceived += (_, args) => { if (args.Data != null) stdErrBuilder.AppendLine(args.Data); };

            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            var timeoutTask = Task.Delay(TimeSpan.FromMinutes(10));
            var exitTask = process.WaitForExitAsync();
            var completedTask = await Task.WhenAny(exitTask, timeoutTask);

            if (completedTask == timeoutTask)
            {
                try { process.Kill(true); } catch { }
                throw new Exception("Python process timed out.");
            }

            await exitTask;

            if (process.ExitCode != 0)
                throw new Exception($"Python script failed:\n{scriptPath}\n\n{stdErrBuilder}");
        }
    }
}