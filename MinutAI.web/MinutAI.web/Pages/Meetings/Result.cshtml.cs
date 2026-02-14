using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using MinutAI.web.Data;
using MinutAI.web.Models;

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
                return RedirectToPage("/Index"); // or a NotFound page

            return Page();
        }
    }
}