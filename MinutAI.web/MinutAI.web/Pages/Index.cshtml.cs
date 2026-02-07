using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Diagnostics;
using System.IO;
using Microsoft.AspNetCore.Authorization;

namespace MinutAI.web.Pages
{
    [Authorize]
    [RequestSizeLimit(300 * 1024 * 1024)]
    public class IndexModel : PageModel
    {
        // Bind as string to avoid checkbox binding edge cases
        [BindProperty]
        public string? ConsentConfirmed { get; set; }

        [BindProperty]
        public IFormFile? AudioFile { get; set; }

        public string? Transcript { get; set; }
        public string? Summary { get; set; }
        public string? ActionItems { get; set; }
        public string? StatusMessage { get; set; }

        public void OnGet() { }

        public void OnPost()
        {
            Console.WriteLine("\n=== OnPost triggered ===");
            Console.WriteLine($"ConsentConfirmed raw: {ConsentConfirmed}");

            if (AudioFile == null || AudioFile.Length == 0)
            {
                StatusMessage = "Please upload an audio file.";
                Console.WriteLine("No file uploaded.");
                return;
            }

            bool consent = ConsentConfirmed == "true" || ConsentConfirmed == "on";
            if (!consent)
            {
                StatusMessage = "Please confirm meeting consent before processing.";
                Console.WriteLine("Consent not confirmed.");
                return;
            }

            // Robust project root detection (works even if app runs from bin\Debug\net8.0)
            var projectRoot = FindProjectRoot();

            Console.WriteLine($"ProjectRoot: {projectRoot}");

            var testAudioDir = Path.Combine(projectRoot, "test_audio");
            var outputsDir = Path.Combine(projectRoot, "outputs");
            var backendDir = Path.Combine(projectRoot, "backend");

            Directory.CreateDirectory(testAudioDir);
            Directory.CreateDirectory(outputsDir);

            var pythonExe = Path.Combine(projectRoot, "venv", "Scripts", "python.exe");
            Console.WriteLine($"PythonExe: {pythonExe}");
            Console.WriteLine($"BackendDir: {backendDir}");

            if (!System.IO.File.Exists(pythonExe))
                throw new FileNotFoundException($"Python venv not found at: {pythonExe}");

            // Save upload with unique name
            var ext = Path.GetExtension(AudioFile.FileName);
            if (string.IsNullOrWhiteSpace(ext)) ext = ".m4a";

            var uniqueFileName = $"meeting_{DateTime.Now:yyyyMMdd_HHmmss}{ext}";
            var uploadedAudioPath = Path.Combine(testAudioDir, uniqueFileName);

            Console.WriteLine($"Saving upload to: {uploadedAudioPath}");

            using (var stream = new FileStream(uploadedAudioPath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite))
            {
                AudioFile.CopyTo(stream);
            }

            // Run pipeline
            StatusMessage = "Step 1/4: Transcribing audio (Whisper)...";
            RunPython(pythonExe, Path.Combine(backendDir, "whisper_test.py"), projectRoot, $"\"{uploadedAudioPath}\"");

            System.Threading.Thread.Sleep(300);

            StatusMessage = "Step 2/4: Cleaning transcript...";
            RunPython(pythonExe, Path.Combine(backendDir, "text_cleaner.py"), projectRoot, "");

            StatusMessage = "Step 3/4: Generating summary...";
            RunPython(pythonExe, Path.Combine(backendDir, "summariser.py"), projectRoot, "");

            StatusMessage = "Step 4/4: Extracting action items...";
            RunPython(pythonExe, Path.Combine(backendDir, "action_extractor.py"), projectRoot, "");

            // Read outputs (shared output files)
            var transcriptPath = Path.Combine(outputsDir, "transcript.txt");
            var summaryPath = Path.Combine(outputsDir, "summary.txt");
            var actionsPath = Path.Combine(outputsDir, "action_items.txt");

            Console.WriteLine($"Reading outputs:\n- {transcriptPath}\n- {summaryPath}\n- {actionsPath}");

            Transcript = System.IO.File.Exists(transcriptPath) ? System.IO.File.ReadAllText(transcriptPath) : null;
            Summary = System.IO.File.Exists(summaryPath) ? System.IO.File.ReadAllText(summaryPath) : null;
            ActionItems = System.IO.File.Exists(actionsPath) ? System.IO.File.ReadAllText(actionsPath) : null;

            StatusMessage = "Processing completed successfully.";
            Console.WriteLine("=== Processing completed successfully ===");
        }

        // Step 1: Robust root finder
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

            throw new Exception("Project root not found. Could not locate 'backend' and 'venv' folders above runtime directory.");
        }

        // Step 3 + timeout + prints output
        private void RunPython(string pythonExe, string scriptPath, string workingDir, string extraArgs)
        {
            Console.WriteLine($"\n--- Running Python ---\n{pythonExe}\n{scriptPath} {extraArgs}\nWorkingDir: {workingDir}");

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

            string stdOut = process.StandardOutput.ReadToEnd();
            string stdErr = process.StandardError.ReadToEnd();

            // Step 4: timeout protection (10 minutes)
            if (!process.WaitForExit(10 * 60 * 1000))
            {
                try { process.Kill(true); } catch { }
                throw new Exception("Python process timed out.");
            }

            if (!string.IsNullOrWhiteSpace(stdOut))
                Console.WriteLine("STDOUT:\n" + stdOut);

            if (!string.IsNullOrWhiteSpace(stdErr))
                Console.WriteLine("STDERR:\n" + stdErr);

            if (process.ExitCode != 0)
                throw new Exception($"Python script failed:\n{scriptPath}\n\n{stdErr}");
        }
    }
}
