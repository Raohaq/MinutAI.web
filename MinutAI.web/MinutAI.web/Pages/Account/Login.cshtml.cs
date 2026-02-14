using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using MinutAI.web.Data;
using System.ComponentModel.DataAnnotations;
using System.Security.Claims;

namespace MinutAI.web.Pages.Account
{
    public class LoginModel : PageModel
    {
        private readonly ApplicationDbContext _db;

        public LoginModel(ApplicationDbContext db)
        {
            _db = db;
        }

        [BindProperty, Required, EmailAddress]
        public string Email { get; set; } = "";

        [BindProperty, Required]
        public string Password { get; set; } = "";

        public string? ErrorMessage { get; set; }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (!ModelState.IsValid)
                return Page();

            var user = await _db.Users.FirstOrDefaultAsync(u => u.Email == Email);
            if (user == null)
            {
                ErrorMessage = "Invalid email or password.";
                return Page();
            }

            // ✅ Verify password using BCrypt (no Identity needed)
            bool valid = BCrypt.Net.BCrypt.Verify(Password, user.PasswordHash);
            if (!valid)
            {
                ErrorMessage = "Invalid email or password.";
                return Page();
            }

            // ✅ Create cookie claims
            var claims = new List<Claim>
            {
                new Claim(ClaimTypes.Name, user.Email),
                new Claim(ClaimTypes.Email, user.Email)
            };

            var identity = new ClaimsIdentity(claims, "Cookies");
            var principal = new ClaimsPrincipal(identity);

            await HttpContext.SignInAsync("Cookies", principal);

            return RedirectToPage("/Index");
        }
    }
}