import Vue from "vue";
import axios from "axios";
import store from "../store.js";
import { eventBus } from "../plugins/event-bus.js";
import { getResponseErrorKey } from "../plugins/vue-i18n.js";

const authAxios = axios.create({
  baseURL: "/"
  // headers: { "Authorization": "Bearer NOT SET" }
});

authAxios.interceptors.response.use(
  resp => {
    return Promise.resolve(resp);
  },
  error => {
    if (error.response.status >= 400) {
      /* display a snack bar with error */
      eventBus.$emit("error", {
        content: getResponseErrorKey(error.response.status),
        action: {
          title: "error-report.actions.report-error",
          func: (vm: Vue) =>
            vm.$router.push({
              name: "error-report",
              query: { redirect: vm.$route.fullPath }
            })
        }
      });
      console.log(error.response);
    }
    if (error.response.status === 401) {
      console.log(error.config);
      store.commit("logOut");
      window.location.replace(
        "login?redirect=" + window.location.toString().replace(/^\/*$/, "")
      );
    }
    return Promise.reject(error);
  }
);

Vue.prototype.$http = authAxios;

export function setJWT(jwt: string) {
  authAxios.defaults.headers.common["Authorization"] = `Bearer ${jwt}`;
}

const plainAxios = axios.create({
  baseURL: "/"
});

Vue.prototype.$httpNoAuth = plainAxios;
