//Tests adding people to the people page
describe("Ensures the Add-person works", function() {
  it("Given: logs in, navigates to people page", function () {
    cy.login();
    cy.get("[data-cy=toggle-nav-drawer]").click();
    cy.get("[data-cy=people]").click();
    cy.url().should("include", "/people");
  });
  it("When: A person without an account is found & the gear is selected", function() {
    cy.get("[data-cy=search]").first().type("Bradley");
    cy.get("[data-cy=account-settings]").first().click();

  });
  it("Then: The add account form should appear & work as intended to create an account", function() {
    //first confirm the fields have restrictions
    cy.get("[data-cy=new-account-username]").type("short");
    cy.get("[data-cy=new-update-password]").type("short");
    cy.get("[data-cy=confirm-password]").type("wrong");
    //all fields should have errors, so now it's time to confirm that there is an error
  });

});
