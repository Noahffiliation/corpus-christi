// Log in
/*describe("Seed for test", () => {
  it("Given: seeding", function() {
    cy.exec("cd ../api && source ./set-up-bash.sh && ./reset-database.sh");
  });
});*/
//if on linux/mac, run this command to reset the database, otherwise
//manually reset the flask database

describe("Tests the Person table Archived/active user filter", function() {
  it("Given: logs in, and navigates to person page, archives an active user",  function() {
    cy.login();
    cy.get("[data-cy=toggle-nav-drawer]").click();
    cy.get("[data-cy=people]").click();
    cy.get("[data-cy=view-dropdown]").should('contain','Ver Activo');
    cy.get('tbody > :nth-child(1) > :nth-child(2)').invoke('text').as('firstName');
    //cy.get('tbody > :nth-child(1) > :nth-child(2)').as('firstName');
    cy.get('tbody > :nth-child(1) [data-cy = deactivate-person]').click();
    });


  it("When: The dropdown is clicked, and an archived users is selected",  function() {
    cy.get("[data-cy=view-dropdown]").click(); // open dropdown
    let dropdown = ".menuable__content__active > .v-select-list > .v-list"; // path to dropdown child elements
    cy.get(dropdown).find(":nth-child(2)").first().click(); //selects view archived users
  });

  it("Then: The archived user should appear in archived, & all, but not active", function() {
    let dropdown = ".menuable__content__active > .v-select-list > .v-list"; // path to dropdown child elements
    cy.get('tbody > :nth-child(1) > :nth-child(2)').should('contain',this.firstName);
    cy.get('[data-cy=deactivate-person').should('not.exist');
    cy.get("[data-cy=view-dropdown]").click(); // open dropdown
    cy.get(dropdown).find(":nth-child(3)").first().click();//selects view all users
    cy.get('tbody > :nth-child(1) > :nth-child(2)').should('contain',this.firstName);
    cy.get('[data-cy=deactivate-person]');//.should('have.attr','deactivate-person');
    cy.get('[data-cy=reactivate-person]');//.should('have.attr','deactivate-person');
    cy.get("[data-cy=view-dropdown]").click(); // open dropdown
    cy.get(dropdown).find(":nth-child(1)").first().click();//selects view active users
    cy.get('tbody > :nth-child(1) > :nth-child(2)').should('not.contain',this.firstName);
    cy.get('[data-cy=reactivate-person').should('not.exist');
  });

  /*it("Then: There should be zero archived users in the table", () => {
    cy.get("tbody > :nth-child(1) > :nth-child(2)").should("not.exist");
  });
  it("And: When a user is archived, they should show up in the archived people", () => {
    //go to active
    cy.get("[data-cy=view-dropdown]").click(); // open dropdown
    cy.get('@dropdown').find(":nth-child(1)")
      .first().click(); // find and click child element in dropdown
    //select first person & deactivate them
    cy.get('tbody > :nth-child(1) > :nth-child(2)').as('firstName');
    cy.get('tbody > :nth-child(1) [data-cy = deactivate-person]').click();
    //make sure they are not there anymore
    cy.get('tbody > :nth-child(1) > :nth-child(2)').should('not.contain','@firstName');

    //go to archived users
    //make sure they are there
    //go to all users, make sure he is first user

    //cy.get("tbody > :nth-child(1) > :nth-child(2)").should("not.exist");
  });
*/
});

