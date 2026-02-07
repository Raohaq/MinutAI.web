using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Authorization;


namespace MinutAI.web.Pages.Account
{
    [AllowAnonymous]
    public class RegisterModel : PageModel
    {
        private readonly UserManager<IdentityUser> _userManager;
        private readonly SignInManager<IdentityUser> _signInManager;

        public RegisterModel(UserManager<IdentityUser> userManager, SignInManager<IdentityUser> signInManager)
        {
            _userManager = userManager;
            _signInManager = signInManager;
        }

        [BindProperty]
        public RegisterInput Input { get; set; } = new();

        public string? ErrorMessage { get; set; }

        public class RegisterInput
        {
            [Required, EmailAddress]
            public string Email { get; set; } = "";

            [Required, MinLength(6)]
            public string Password { get; set; } = "";

            [Required, Compare(nameof(Password))]
            public string ConfirmPassword { get; set; } = "";
        }

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (!ModelState.IsValid) return Page();

            var user = new IdentityUser
            {
                UserName = Input.Email,
                Email = Input.Email,
                EmailConfirmed = true
            };

            var result = await _userManager.CreateAsync(user, Input.Password);

            if (!result.Succeeded)
            {
                ErrorMessage = string.Join(" | ", result.Errors.Select(e => e.Description));
                return Page();
            }

            await _signInManager.SignInAsync(user, isPersistent: false);
            return RedirectToPage("/Index");
        }
    }
}
