using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using MinutAI.web.Data;
using MinutAI.web.Models;
using System.IO.Compression;
using System.Text;

namespace MinutAI.web.Pages.Meetings
{
    [Authorize]
    public class HistoryModel : PageModel
    {
        private readonly ApplicationDbContext _db;

        public HistoryModel(ApplicationDbContext db)
        {
            _db = db;
        }

        public List<MeetingRecord> Meetings { get; set; } = new();

        public async Task OnGetAsync()
        {
            var userEmail = User.Identity?.Name ?? "";

            Meetings = await _db.Meetings
                .Where(m => m.UserEmail == userEmail)
                .OrderByDescending(m => m.CreatedAt)
                .ToListAsync();
        }

        public async Task<IActionResult> OnPostDeleteAsync(int id)
        {
            var userEmail = User.Identity?.Name ?? "";

            await _db.Meetings
                .Where(m => m.Id == id && m.UserEmail == userEmail)
                .ExecuteDeleteAsync();

            return RedirectToPage();
        }

        // ✅ Download ZIP handler
        public IActionResult OnGetDownloadZip(int id)
        {
            var userEmail = User.Identity?.Name ?? "";

            var meeting = _db.Meetings
                .FirstOrDefault(m => m.Id == id && m.UserEmail == userEmail);

            if (meeting == null)
                return RedirectToPage();

            using var ms = new MemoryStream();
            using (var zip = new ZipArchive(ms, ZipArchiveMode.Create, leaveOpen: true))
            {
                AddTextFile(zip, "transcript.txt", meeting.Transcript ?? "");
                AddTextFile(zip, "summary.txt", meeting.Summary ?? "");
                AddTextFile(zip, "action_items.txt", meeting.ActionItems ?? "");
            }

            ms.Position = 0;
            var fileName = $"MinutAI_Meeting_{meeting.Id}_outputs.zip";
            return File(ms.ToArray(), "application/zip", fileName);
        }
       

        private static void AddTextFile(ZipArchive zip, string fileName, string content)
        {
            var entry = zip.CreateEntry(fileName);
            using var entryStream = entry.Open();
            using var writer = new StreamWriter(entryStream, Encoding.UTF8);
            writer.Write(content);
        }

        public string Preview(string? text, int maxLen = 120)
        {
            if (string.IsNullOrWhiteSpace(text)) return "";
            text = text.Replace("\r", " ").Replace("\n", " ").Trim();
            return text.Length <= maxLen ? text : text.Substring(0, maxLen) + "...";
        }
    }
}