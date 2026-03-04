using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using MinutAI.web.Data;
using MinutAI.web.Models;
using System.Text;
using System.IO.Compression;

namespace MinutAI.web.Pages.Meetings
{
    [Authorize]
    public class ResultModel : PageModel
    {
        private readonly ApplicationDbContext _db;

        public ResultModel(ApplicationDbContext db)
        {
            _db = db;
        }

        public MeetingRecord? Meeting { get; set; }

        public IActionResult OnGet(int id)
        {
            var userEmail = User.Identity?.Name ?? "";
            Meeting = _db.Meetings.FirstOrDefault(m => m.Id == id && m.UserEmail == userEmail);

            if (Meeting == null)
                return RedirectToPage("/Index");

            return Page();
        }

        // Download handler: /Meetings/Result?id=1&handler=Download&type=summary
        public IActionResult OnGetDownload(int id, string type)
        {
            var userEmail = User.Identity?.Name ?? "";
            var meeting = _db.Meetings.FirstOrDefault(m => m.Id == id && m.UserEmail == userEmail);

            if (meeting == null)
                return RedirectToPage("/Index");

            string content;
            string fileName;

            switch (type?.ToLower())
            {
                case "transcript":
                    content = meeting.Transcript ?? "";
                    fileName = $"transcript_{meeting.Id}.txt";
                    break;

                case "summary":
                    content = meeting.Summary ?? "";
                    fileName = $"summary_{meeting.Id}.txt";
                    break;

                case "actions":
                    content = meeting.ActionItems ?? "";
                    fileName = $"action_items_{meeting.Id}.txt";
                    break;

                default:
                    return RedirectToPage("/Meetings/Result", new { id = meeting.Id });
            }

            var bytes = Encoding.UTF8.GetBytes(content);
            return File(bytes, "text/plain", fileName);
        }

        // Download all as ZIP: /Meetings/Result?id=1&handler=DownloadAll
        public IActionResult OnGetDownloadAll(int id)
        {
            var userEmail = User.Identity?.Name ?? "";
            var meeting = _db.Meetings.FirstOrDefault(m => m.Id == id && m.UserEmail == userEmail);

            if (meeting == null)
                return RedirectToPage("/Index");

            using var ms = new MemoryStream();

            using (var zip = new ZipArchive(ms, ZipArchiveMode.Create, leaveOpen: true))
            {
                AddTextFile(zip, "transcript.txt", meeting.Transcript ?? "");
                AddTextFile(zip, "summary.txt", meeting.Summary ?? "");
                AddTextFile(zip, "action_items.txt", meeting.ActionItems ?? "");
            }

            ms.Position = 0;
            var zipName = $"MinutAI_Meeting_{meeting.Id}_Outputs.zip";
            return File(ms.ToArray(), "application/zip", zipName);
        }

        private static void AddTextFile(ZipArchive zip, string fileName, string content)
        {
            var entry = zip.CreateEntry(fileName);
            using var entryStream = entry.Open();
            using var writer = new StreamWriter(entryStream, Encoding.UTF8);
            writer.Write(content);
        }
    }
}