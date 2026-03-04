using System.ComponentModel.DataAnnotations;

namespace MinutAI.web.Models
{
    public class AppUser
    {
        public int Id { get; set; }

        [Required]
        public string FullName { get; set; } = "";

        [Required]
        public string Email { get; set; } = "";

        [Required]
        public string PasswordHash { get; set; } = "";
    }
}