export const dailyCalls = [
  { day: "Mon", calls: 420, answered: 318, conversions: 44 },
  { day: "Tue", calls: 510, answered: 386, conversions: 61 },
  { day: "Wed", calls: 610, answered: 461, conversions: 78 },
  { day: "Thu", calls: 560, answered: 414, conversions: 72 },
  { day: "Fri", calls: 720, answered: 548, conversions: 96 },
  { day: "Sat", calls: 390, answered: 248, conversions: 31 },
  { day: "Sun", calls: 330, answered: 211, conversions: 27 },
];

export const callOutcomes = [
  { name: "Converted", value: 34 },
  { name: "Interested", value: 27 },
  { name: "No Answer", value: 22 },
  { name: "Rejected", value: 17 },
];

export const revenueAnalytics = [
  { campaign: "Solar", revenue: 42000, conversions: 88 },
  { campaign: "Fintech", revenue: 31000, conversions: 63 },
  { campaign: "Clinic", revenue: 22500, conversions: 48 },
  { campaign: "SaaS", revenue: 54800, conversions: 112 },
  { campaign: "Realty", revenue: 38400, conversions: 74 },
];

export const recentActivity = [
  { id: 1, callerName: "Priya Menon", phone: "+91 98765 43120", agent: "Sarah - Sales", duration: "04:38", status: "Converted", date: "Jun 11, 10:42" },
  { id: 2, callerName: "Marcus Lee", phone: "+1 415 555 0198", agent: "Maya - Support", duration: "02:15", status: "Follow-up", date: "Jun 11, 10:21" },
  { id: 3, callerName: "Aarav Shah", phone: "+91 99887 76655", agent: "Nora - Billing", duration: "01:46", status: "No Answer", date: "Jun 11, 09:58" },
  { id: 4, callerName: "Elena Cruz", phone: "+1 212 555 0114", agent: "Aiden - Demo", duration: "06:09", status: "Interested", date: "Jun 10, 17:35" },
  { id: 5, callerName: "Rohan Iyer", phone: "+91 91234 88002", agent: "Sarah - Sales", duration: "03:22", status: "Transferred", date: "Jun 10, 16:19" },
];

export const agents = [
  { id: 1, name: "Sarah", voice: "Alloy", language: "English", purpose: "Lead qualification", active: true, calls: 12840, industry: "SaaS" },
  { id: 2, name: "Nora", voice: "Shimmer", language: "English + Hindi", purpose: "Billing reminders", active: true, calls: 8230, industry: "Fintech" },
  { id: 3, name: "Maya", voice: "Anushka", language: "Hindi", purpose: "Appointment confirmation", active: false, calls: 5120, industry: "Healthcare" },
  { id: 4, name: "Aiden", voice: "Echo", language: "English", purpose: "Product demos", active: true, calls: 10420, industry: "Real estate" },
];

export const campaigns = [
  { id: 1, name: "June Demo Follow-up", audience: "Inbound demo leads", contacts: 2480, completed: 1864, success: 38, status: "Running" },
  { id: 2, name: "Clinic Appointment Reminder", audience: "Patients tomorrow", contacts: 780, completed: 622, success: 81, status: "Running" },
  { id: 3, name: "Renewal Win-back", audience: "Expired subscriptions", contacts: 1430, completed: 1430, success: 24, status: "Completed" },
  { id: 4, name: "Delivery Confirmation", audience: "Orders out for delivery", contacts: 960, completed: 0, success: 0, status: "Draft" },
];

export const contacts = [
  { id: 1, name: "Priya Menon", phone: "+91 98765 43120", email: "priya@zencrm.io", company: "ZenCRM", lastContacted: "Today", status: "Qualified" },
  { id: 2, name: "Marcus Lee", phone: "+1 415 555 0198", email: "marcus@northstar.ai", company: "Northstar AI", lastContacted: "Today", status: "Follow-up" },
  { id: 3, name: "Elena Cruz", phone: "+1 212 555 0114", email: "elena@havenhomes.com", company: "Haven Homes", lastContacted: "Yesterday", status: "Interested" },
  { id: 4, name: "Aarav Shah", phone: "+91 99887 76655", email: "aarav@mintpay.in", company: "MintPay", lastContacted: "Jun 9", status: "No Answer" },
  { id: 5, name: "Sofia Patel", phone: "+44 20 7946 0958", email: "sofia@medica.co", company: "Medica Clinics", lastContacted: "Jun 8", status: "Converted" },
];

export const activeCalls = [
  {
    id: "live-1288",
    customer: "Daniel Weber",
    agent: "Sarah - Sales",
    duration: "05:12",
    transcript: ["AI: Thanks for taking the call, Daniel.", "Customer: I am comparing two providers.", "AI: I can summarize pricing and transfer you to a specialist."],
  },
  {
    id: "live-1291",
    customer: "Nisha Rao",
    agent: "Maya - Appointments",
    duration: "01:38",
    transcript: ["AI: Your consultation is scheduled for tomorrow at 4 PM.", "Customer: Can I move it to Friday?", "AI: I can help with that."],
  },
  {
    id: "live-1296",
    customer: "Theo Martin",
    agent: "Nora - Billing",
    duration: "03:44",
    transcript: ["AI: I am calling about invoice INV-4021.", "Customer: We paid yesterday.", "AI: Thank you, I will mark that for verification."],
  },
];

export const callLogs = [
  { id: "CALL-88201", customer: "Priya Menon", agent: "Sarah", duration: "04:38", outcome: "Converted", recording: "Ready", transcript: "Ready" },
  { id: "CALL-88200", customer: "Rohan Iyer", agent: "Sarah", duration: "03:22", outcome: "Transferred", recording: "Ready", transcript: "Ready" },
  { id: "CALL-88198", customer: "Aarav Shah", agent: "Nora", duration: "01:46", outcome: "No Answer", recording: "None", transcript: "Partial" },
  { id: "CALL-88194", customer: "Elena Cruz", agent: "Aiden", duration: "06:09", outcome: "Interested", recording: "Ready", transcript: "Ready" },
];

export const knowledgeDocs = [
  { id: 1, name: "Pricing FAQ", type: "PDF", status: "Synced" },
  { id: 2, name: "Product demo script", type: "Document", status: "Training" },
  { id: 3, name: "Refund policy URL", type: "URL", status: "Synced" },
  { id: 4, name: "Objection handling", type: "Sheet", status: "Needs review" },
];

export const phoneNumbers = [
  { id: 1, number: "+1 415 555 0134", country: "United States", provider: "Twilio", status: "Active", type: "Purchased" },
  { id: 2, number: "+91 80 4567 1200", country: "India", provider: "Vobiz", status: "Active", type: "Purchased" },
  { id: 3, number: "+44 20 7946 0301", country: "United Kingdom", provider: "Telnyx", status: "Available", type: "Available" },
  { id: 4, number: "+61 2 8015 2202", country: "Australia", provider: "Twilio", status: "Available", type: "Available" },
];

export const agentPerformance = [
  { agent: "Sarah", calls: 840, conversions: 168, csat: 94 },
  { agent: "Nora", calls: 620, conversions: 91, csat: 89 },
  { agent: "Maya", calls: 540, conversions: 132, csat: 96 },
  { agent: "Aiden", calls: 710, conversions: 118, csat: 91 },
];
