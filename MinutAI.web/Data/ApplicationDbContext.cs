using Microsoft.EntityFrameworkCore;
using MinutAI.web.Models;

namespace MinutAI.web.Data
{
    public class ApplicationDbContext : DbContext
    {

        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<AppUser> Users { get; set; } = default!;
        public DbSet<MeetingRecord> Meetings { get; set; } = default!;
    }
}