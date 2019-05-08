import { unique_id } from '../../support/helpers';

let diploma_title = unique_id();

// Tests button functionality 
describe("Diplomas Page General Testing", () => { 
  it("GIVEN: Successful login", () => {
    cy.login();
  });

  it("WHEN: Clicking to diplomas page", () => {
    cy.deploma_page()
  });

  it("THEN: Should be in diplomas page", () => {
    cy.url().should("include", "/diplomas");
  });
});

describe("Fill out new diploma form", () => {
  it("GIVEN: Form is loaded", () => {
    cy.get("[data-cy=diplomas-table-new]").click();
  });

  it("THEN: Fill-out new diploma form", () => {
    cy.get("[data-cy=diplomas-form-name]").type(diploma_title); // Title
    cy.get("[data-cy=diploma-form-description]").type("Epic Dance Party"); // Description
    cy.get(":nth-child(4) > .v-input__icon > .v-icon").click(); // Click drop down
    cy.get(".menuable__content__active > .v-select-list > .v-list > :nth-child(1) > .v-list__tile").click(); // Select an item from the drop down
    cy.get(":nth-child(4) > .v-input__icon > .v-icon").click(); // Click drop down
    cy.get(".menuable__content__active > .v-select-list > .v-list > :nth-child(1) > .v-list__tile").click(); // Select another item from the drop down
  });

  it("THEN: Click save button", () => {
  	cy.get("[data-cy=form-save]").click();
  });
});

describe('Archive and Activate diploma', () => {
  it('Archive diploma', () => {
    cy.get("[data-cy=diplomas-table-search]").clear();
    cy.get("[data-cy=diplomas-table-search]").type(diploma_title);

    // Archive the first diploma
    cy.get(':nth-child(1) > :nth-child(3) > .layout > :nth-child(2) > span > .v-btn').click();

    // Confirmation button
    cy.get("[data-cy=confirm-archive]").click();
    cy.get(".v-snack__content"); // Snack-bar
  });

  it("Search for archived diploma", () => {
  	// View archived diplomas
   	cy.get(":nth-child(5) > .v-input > .v-input__control > .v-input__slot > .v-select__slot").click();
    cy.get(".menuable__content__active > .v-select-list > .v-list > :nth-child(2) > .v-list__tile").click();

    cy.get("[data-cy=diplomas-table-search]").clear();
    cy.get("[data-cy=diplomas-table-search]").type(diploma_title);
  });

  it("Re-activate diploma", () => {
    cy.get(':nth-child(1) > :nth-child(3) > .layout > :nth-child(2) > span > .v-btn').click();
    cy.get(".v-snack__content"); // Snack-bar
  });

  it("Find re-activated diploma in active table", () => {
  	// Show active diplomas
    cy.get(':nth-child(5) > .v-input > .v-input__control > .v-input__slot > .v-select__slot').click();
    cy.get('.menuable__content__active > .v-select-list > .v-list > :nth-child(1) > .v-list__tile').click();

    // Search for re-activated diploma
    cy.get("[data-cy=diplomas-table-search]").clear();
    cy.get("[data-cy=diplomas-table-search]").type(diploma_title);

    // Find the first element
    cy.get("tbody > tr > :nth-child(1)").contains(diploma_title);
  });
});