<template>
  <div>
    <v-container fluid fill-height>
      <v-layout align-center justify-center>
        <v-flex xs12 sm8 md6>
          <v-card class="elevation-12">
            <v-toolbar dark color="primary">
              <v-toolbar-title>{{ $t("login.header") }}</v-toolbar-title>
              <v-spacer></v-spacer>
            </v-toolbar>
            <v-card-text>
              <v-form>
                <v-text-field
                  v-model="username"
                  v-bind:label="$t('person.username')"
                  prepend-icon="person"
                  name="login"
                  type="text"
                  v-on:keyup.enter="login"
                  data-cy="username"
                />
                <v-text-field
                  v-model="password"
                  v-bind:label="$t('person.password')"
                  prepend-icon="lock"
                  name="password"
                  type="password"
                  v-on:keyup.enter="login"
                  data-cy="password"
                />
              </v-form>
              <v-flex>
                {{ $t("person.no-account") }}
                <router-link v-bind:to="{ name: 'signup' }" data-cy="signup">
                  <a class="href" v-text="$t('actions.signup')" />
                </router-link>
              </v-flex>
            </v-card-text>
            <v-card-actions>
              <v-layout fill-height justify-end align-end column xs12>
                <v-flex>
                  <v-btn text v-on:click="cancel" data-cy="cancel">
                    {{ $t("actions.cancel") }}
                  </v-btn>
                  <v-btn color="primary" v-on:click="login" data-cy="login">
                    {{ $t("actions.login") }}
                  </v-btn>
                </v-flex>
              </v-layout>
            </v-card-actions>
          </v-card>
        </v-flex>
      </v-layout>
    </v-container>
  </div>
</template>

<script>
import { mapMutations } from "vuex";
import Account from "../models/Account";
import jwtDecode from "jwt-decode";
import { eventBus } from "@/plugins/event-bus";

export default {
  name: "Login",
  data() {
    return {
      username: "",
      password: "",
    };
  },

  methods: {
    ...mapMutations(["logIn"]),

    cancel() {
      this.$router.push({ name: "public" });
    },

    async login() {
      try {
        const resp = await this.$httpNoAuth.post("/api/v1/auth/login", {
          username: this.username,
          password: this.password,
        });
        if (resp.status !== 200) {
          console.error(`JWT STATUS ${resp.status}`);
          return;
        } else {
          const decodedJwt = jwtDecode(resp.data.jwt);
          this.logIn({
            account: new Account(
              resp.data.username,
              resp.data.firstName,
              resp.data.lastName,
              decodedJwt.user_claims.roles,
              resp.data.id,
              resp.data.email
            ),
            jwt: resp.data.jwt,
          });

          console.log("RESP", resp.status);
          // Normally want to use `push`, but unlikely that
          // the user wants to return to the login page.
          const route = this.$route.query.redirect || { name: "people" };
          await this.$router.replace(route);
        }
      } catch (err) {
        console.log(err);
        eventBus.$emit("error", {
          content: "login.messages.incorrect-login",
        });
      }
    },
  },
};
</script>
