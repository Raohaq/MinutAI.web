using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Authorization;


namespace MinutAI.web.Pages.Account
{
    [AllowAnonymous]
    public class LoginModel : PageModel
    {
        private readonly SignInManager<IdentityUser> _signInManager;

        public LoginModel(SignInManager<IdentityUser> signInManager)
        {
            _signInManager = signInManager;
        }

        [BindProperty]
        public LoginInput Input { get; set; } = new();

        public string? ErrorMessage { get; set; }

        public class LoginInput
        {
            [Required, EmailAddress]
            public string Email { get; set; } = "";

            [Required]
            public string Password { get; set; } = "";
        }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (!ModelState.IsValid) return Page();

            var result = await _signInManager.PasswordSignInAsync(
                Input.Email, Input.Password, isPersistent: false, lockoutOnFailure: false);

            if (!result.Succeeded)
            {
                ErrorMessage = "Invalid login attempt. Check your email and password.";
                return Page();
            }

            return RedirectToPage("/Index");
        }
    }
}