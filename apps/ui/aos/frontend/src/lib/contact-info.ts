/**
 * Single source of truth for marketing contact information.
 *
 * Edit this file to update emails / social URLs / addresses across the
 * marketing site (contact page, security page vulnerability email, footer
 * status badge, blog author bylines, etc.). All marketing pages import from
 * here — no copy lives in component files.
 */

export const CONTACT_INFO = {
  /** Public-facing inboxes. */
  emails: {
    support: "nabinoli2004@gmail.com",
    sales: "nabinoli2004@gmail.com",
    security: "nabinoli2004@gmail.com",
    privacy: "nabinoli2004@gmail.com",
    legal: "nabinoli2004@gmail.com",
    press: "nabinoli2004@gmail.com",
  },
  /** Social handles. Used as `https://{platform}.com/{handle}` or absolute URLs. */
  socials: {
    twitter: "https://twitter.com",
    github: "https://github.com/nabin2004/AOS",
    discord: "https://discord.gg",
    youtube: "https://youtube.com",
    linkedin: "https://linkedin.com",
  },
  /** Working hours hint shown on contact page. */
  workingHours: "UTC 08:00–18:00",
  /** Optional physical address — leave empty if remote-only. */
  address: null as string | null,
  /** SLA promise displayed near the form. */
  responseSla: "24h",
};
