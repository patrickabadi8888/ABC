## Applicant

- [ ] Can only view the list of projects that are:
  - Open to their user group (Single or Married)
  - Visibility toggled “on”
- [x] Able to apply for a project – cannot apply for multiple projects
  - Singles (35 years old and above) can ONLY apply for 2-Room
  - Married (21 years old and above) can apply for any flat types (2-Room or 3-Room)
- [x] Able to view the project he/she applied for, even after visibility is turned off, and the application status:
  - **Pending**: Entry status upon application – no conclusive decision made
  - **Successful**: Outcome of the application is successful; invited to make a flat booking with the HDB Officer
  - **Unsuccessful**: Outcome of the application is unsuccessful; cannot make a flat booking for this application. Applicant may apply for another project.
  - **Booked**: Secured a unit after a successful application and completed a flat booking with the HDB Officer
- [x] If Application status is “Successful,” Applicant can book **one** flat through the HDB Officer (cannot book more than one flat, within or across different projects)
- [x] Allowed to request withdrawal for their BTO application before/after flat booking
- [x] Able to submit enquiries (a string) regarding the projects
- [x] Able to view, edit, and delete their enquiries

---

## HDB Officer

- [ ] Possesses all Applicant capabilities
- [ ] Able to register to join a project if:
  - They have **no intention to apply** for the project as an Applicant (cannot apply before or after becoming an HDB Officer of that project)
  - They are **not** already an HDB Officer for another project within the application period (from application opening date to application closing date)
- [ ] Able to see the status of their registration to be an HDB Officer for a project
- [ ] Registration is subject to approval from the HDB Manager in charge of the project
  - Once approved, their profile will reflect the project they are an HDB Officer for
- [ ] Able to apply for other projects in which he/she is **not** handling – once applied for a BTO project, he/she cannot register to handle the same project
- [ ] Able to view the details of the project they are handling regardless of visibility
- [ ] Not allowed to edit the project details
- [ ] Able to view and reply to enquiries regarding the project they are handling
- [ ] With Applicant’s successful BTO application, HDB Officer’s **flat selection responsibilities**:
  - [ ] Update the number of remaining flats for each flat type
  - [ ] Retrieve applicant’s BTO application with applicant’s NRIC
  - [ ] Update applicant’s project status from “Successful” to “Booked”
  - [ ] Update applicant’s profile with the flat type (2-Room or 3-Room) chosen
- [ ] Able to generate a receipt of the applicants with their flat booking details (Name, NRIC, age, marital status, flat type booked, project details)

---

## HDB Manager

- [ ] Able to create, edit, and delete BTO project listings
- [ ] A BTO project information includes:
  - Project Name
  - Neighborhood (e.g. Yishun, Boon Lay, etc.)
  - Types of Flat (assume only 2-Room and 3-Room)
  - Number of units for the respective flat types
  - Application opening date
  - Application closing date
  - HDB Manager in charge (automatically tied to the creator)
  - Available HDB Officer Slots (max 10)
- [ ] Can only handle one project within an application period (from application opening date to application closing date)
- [ ] Able to toggle the visibility of the project to “on” or “off”
- [ ] Able to view **all** created projects (including those created by other HDB Managers), regardless of visibility
- [ ] Able to filter and view the list of projects they have created
- [ ] Able to view pending and approved HDB Officer registrations
- [ ] Able to approve or reject HDB Officer’s registration (as the HDB Manager in charge) – also updates project’s remaining HDB Officer slots
- [x] Able to approve or reject Applicant’s BTO application (approval is limited by the supply of flats)
- [x] Able to approve or reject Applicant’s request to withdraw the application
- [ ] Able to generate a report of the list of applicants with their respective flat booking:
  - Includes filters for categories (e.g. report of married applicants’ choice of flat type)
- [ ] Cannot apply for any BTO project as an Applicant
- [ ] Able to view enquiries of **all** projects
- [ ] Able to view and reply to enquiries regarding the project they are handling

---

- [ ] Convert getusertype to user function