<template>
  <div>
    <!-- show the cycle in hierarchy if there is one -->
    <v-card v-if="cycleError.show" flat>
      <v-card-title class="justify-center">
        <v-alert type="warning" :icon="false">
          <v-tooltip bottom>
            <template v-slot:activator="{ on }">
              <v-icon v-on="on" x-large>error</v-icon>
            </template>
            {{ $t("groups.treeview.remove-cycle") }}
          </v-tooltip>
          {{ $t("groups.treeview.unexpected-cycle") }}:
          {{ cycleError.node.toHumanReadable() }}
        </v-alert>
      </v-card-title>
      <v-card-text>
        <v-timeline v-if="cycleError.path.length !== 0">
          <v-timeline-item
            v-for="(node, i) in cycleError.path"
            :key="i"
            :color="node.equal(cycleError.node) ? 'error' : 'primary'"
            :class="i % 2 ? 'text-right' : ''"
          >
            <span v-if="node.nodeType === 'Group'">
              <v-icon>people</v-icon>
              <router-link
                :to="{
                  name: 'group-details',
                  params: { group: node.getObject().id },
                }"
              >
                {{ node.toHumanReadable() }}
              </router-link>
            </span>
            <span v-else>
              <v-icon>person</v-icon>
              {{ node.toHumanReadable() }}
            </span>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>
    </v-card>
    <v-card v-else flat>
      <v-toolbar flat class="pa-1">
        <v-row no-gutters align="center" justify="space-between">
          <v-col cols="8">
            <v-text-field
              :append-icon="search ? 'clear' : 'search'"
              @click:append="search = ''"
              :label="$t('actions.search')"
              v-model="search"
            >
            </v-text-field>
          </v-col>
          <v-spacer />
          <v-col class="shrink">
            <v-tooltip bottom
              ><template v-slot:activator="{ on }">
                <v-btn color="primary" fab small @click="expandAll" v-on="on"
                  ><v-icon>unfold_more</v-icon></v-btn
                >
              </template>
              {{ $t("groups.treeview.expand") }}
            </v-tooltip>
          </v-col>
          <v-col class="shrink">
            <v-tooltip bottom
              ><template v-slot:activator="{ on }">
                <v-btn
                  color="grey lighten-2"
                  fab
                  small
                  @click="closeAll"
                  v-on="on"
                  ><v-icon>unfold_less</v-icon></v-btn
                >
              </template>
              {{ $t("groups.treeview.collapse") }}
            </v-tooltip>
          </v-col>
        </v-row>
      </v-toolbar>
      <v-card-text>
        <v-treeview
          :items="treeItems"
          :search="search"
          ref="treeview"
          activatable
          transition
          hoverable
          open-on-click
          return-object
        >
          <template v-slot:prepend="{ item }">
            <v-icon v-if="item.nodeType === 'Group'" color="primary"
              >group</v-icon
            >
            <v-icon v-else-if="item.nodeType === 'Participant'">person</v-icon>
            <v-icon v-else-if="item.nodeType === 'Admin'"
              >supervised_user_circle</v-icon
            >
          </template>
          <template v-slot:label="{ item }">
            <router-link
              v-if="item.nodeType === 'Group'"
              :to="{ name: 'group', params: { group: item.info.id } }"
              >{{ item.name }}</router-link
            >
            <span v-else>{{ item.name }}</span>
          </template>
        </v-treeview>
      </v-card-text>
    </v-card>
  </div>
</template>
<script>
import {
  Group,
  Participant,
  count,
  convertToGroupMap,
  getInfoTree,
  HierarchyCycleError,
  isRootNode,
  getParticipantById,
} from "../../../models/GroupHierarchyNode.ts";
import { eventBus } from "../../../plugins/event-bus.js";
import { mapState } from "vuex";
export default {
  name: "TreeviewHierarchy",
  props: {
    groups: Array,
    persons: Array,
    isAdminMode: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      search: "",
      cycleError: {
        show: false,
        path: [],
        node: null,
      },
    };
  },
  methods: {
    expandAll() {
      this.$refs["treeview"].updateAll(true);
    },
    closeAll() {
      this.$refs["treeview"].updateAll(false);
    },
  },
  computed: {
    groupMap() {
      return convertToGroupMap(this.groups);
    },
    treeItems() {
      return this.isAdminMode ? this.adminTree : this.managerTree;
    },
    managerTree() {
      let currentParticipant = getParticipantById(
        this.currentAccount.id,
        this.groupMap
      );
      return currentParticipant ? [getInfoTree(currentParticipant)] : [];
    },
    adminTree() {
      let counter = count();
      // get all root groups and root participants
      let rootNodes = [
        ...this.groups.map(
          (groupObject) => new Group(groupObject, this.groupMap)
        ),
        ...this.persons.map(
          (person) => new Participant({ person }, this.groupMap)
        ),
      ].filter((node) => isRootNode(node));
      const treeNodes = rootNodes.map((rootNode) => {
        try {
          return getInfoTree(rootNode, false, counter);
        } catch (err) {
          if (err instanceof HierarchyCycleError) {
            this.cycleError.show = true;
            this.cycleError.node = err.node;
            this.cycleError.path = err.path;
            eventBus.$emit("error", {
              content: "groups.treeview.unexpected-cycle",
            });
          } else {
            throw err;
          }
        }
      });
      return treeNodes;
    },
    ...mapState(["currentAccount"]),
  },
};
</script>
