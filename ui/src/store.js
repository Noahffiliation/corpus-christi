// Vuex store; contains global state information for the entire UI.

import Vue from "vue";
import Vuex from "vuex";
import { setJWT } from "./plugins/axios";
import { Locale, LocaleModel } from "./models/Locale";
import createPersistedState from "vuex-persistedstate";
import { persistedStateOptions } from "./plugins/vuex-persistedstate.js";

Vue.use(Vuex);

export default new Vuex.Store({
  plugins: [createPersistedState(persistedStateOptions)],

  state: {
    // Current locale code (e.g., `es-EC`, `en-US`)
    currentLocale: new Locale("es-EC"),

    // All available I18NLocale instances (locale and description).
    localeModels: [],

    // Current `Account` object if someone logged in.
    currentAccount: null,

    // Current JSON Web Token if someone logged in.
    currentJWT: null,

    // All translations for the currentLocale
    translations: [],
  },

  getters: {
    // Is there a currently logged-in user?
    isLoggedIn(state) {
      return state.currentJWT && state.currentAccount;
    },

    currentLocaleModel(state) {
      // console.log("localeModel", localeModel)
      return state.localeModels.find(
        (localeModel) =>
          localeModel.locale.languageCode === state.currentLocale.languageCode
      );
    },

    currentLanguageCode(state) {
      const currentLocaleModel = state.localeModels.find(
        (localeModel) =>
          localeModel.locale.languageCode === state.currentLocale.languageCode
      );
      if (currentLocaleModel) {
        return currentLocaleModel.languageCode;
      } else {
        throw Error("No current language code");
      }
    },
  },

  mutations: {
    logIn(state, payload) {
      state.currentAccount = payload.account;
      state.currentJWT = payload.jwt;
      setJWT(payload.jwt);
    },

    logOut(state) {
      state.currentAccount = null;
      state.currentJWT = null;
    },

    setCurrentLocale(state, locale) {
      state.currentLocale = locale;
    },

    setLocaleModels(state, inputLocaleModels) {
      state.localeModels = inputLocaleModels.map(
        (inputLocaleModel) => new LocaleModel(inputLocaleModel)
      );
    },
  },
});
