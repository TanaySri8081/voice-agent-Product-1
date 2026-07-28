// Per-vertical display labels. The app stays clinic-neutral in code (routes,
// DB, API keep generic names); only the UI wording adapts to the tenant's
// industry. `contact` = the person the AI talks to; `booking` = what it books.
export const VERTICAL_LABELS = {
  clinic:      { contact: "Patient",  contacts: "Patients",  booking: "Appointment", bookings: "Appointments" },
  real_estate: { contact: "Lead",     contacts: "Leads",     booking: "Site Visit",  bookings: "Site Visits" },
  restaurant:  { contact: "Guest",    contacts: "Guests",    booking: "Reservation", bookings: "Reservations" },
  salon:       { contact: "Client",   contacts: "Clients",   booking: "Appointment", bookings: "Appointments" },
  services:    { contact: "Customer", contacts: "Customers", booking: "Job",         bookings: "Jobs" },
  general:     { contact: "Contact",  contacts: "Contacts",  booking: "Booking",     bookings: "Bookings" },
};

export function labelsFor(industry) {
  return VERTICAL_LABELS[industry] || VERTICAL_LABELS.general;
}
