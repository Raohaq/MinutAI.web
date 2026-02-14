using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using MinutAI.web.Data;
using MinutAI.web.Models;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;

namespace MinutAI.web.Pages.Account
{
    public class RegisterModel : PageModel
    {
        private readonly ApplicationDbContext _db;

        public RegisterModel(ApplicationDbContext db)
        {
            _db = db;
        }

        [BindProperty, Required]
        public string FullName { get; set; } = "";

        [BindProperty, Required, EmailAddress]
        public string Email { get; set; } = "";

        [BindProperty, Required]
        public string Password { get; set; } = "";

        [BindProperty, Required]
        public string ConfirmPassword { get; set; } = "";

        public string? ErrorMessage { get; set; }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (!ModelState.IsValid)
                return Page();

            if (Password != ConfirmPassword)
            {
                ErrorMessage = "Passwords do not match.";
                return Page();
            }

            // Check if email already exists
            var exists = await _db.Users.AnyAsync(u => u.Email == Email);
            if (exists)
            {
                ErrorMessage = "This email is already registered.";
                return Page();
            }

            // Create user + hash password with BCrypt (no Identity)
            var user = new AppUser
            {
                FullName = FullName,
                Email = Email,
                PasswordHash = BCrypt.Net.BCrypt.HashPassword(Password)
            };

            _db.Users.Add(user);
            await _db.SaveChangesAsync();

            // Redirect to upload page
            return RedirectToPage("/Index");
        }
    }
}