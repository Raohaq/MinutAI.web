using System;
using System.ComponentModel.DataAnnotations;

namespace MinutAI.web.Models
{
    public class MeetingRecord
    {
        public int Id { get; set; }

        [Required]
        public string UserEmail { get; set; } = "";

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public string AudioFileName { get; set; } = "";
        public string Transcript { get; set; } = "";
        public string Summary { get; set; } = "";
        public string ActionItems { get; set; } = "";
    }
}
