<template>
  <div>
    <!-- Interior node -->
    <v-list-group v-if="isInterior">
      <template v-slot:activator>
        <v-list-item-icon>
          <v-icon>{{ item.icon }}</v-icon>
        </v-list-item-icon>
        <v-list-item-title>{{ item.title }}</v-list-item-title>
      </template>

      <nav-item
        v-for="child in item.children"
        :key="child.route"
        :item="child"
        :isChild="true"
      />
    </v-list-group>

    <!-- Leaf node   -->
    <v-list-item
      v-else-if="isLeaf"
      :to="{ name: item.route }"
      :data-cy="item.route"
    >
      <v-list-item-action v-if="item.icon && !item.isDropdown">
        <v-icon>{{ item.icon }}</v-icon>
      </v-list-item-action>
      <v-list-item-title>
        {{ item.title }}
      </v-list-item-title>
      <v-list-item-action v-if="item.icon && item.isDropdown">
        <v-icon>{{ item.icon }}</v-icon>
      </v-list-item-action>
    </v-list-item>
  </div>
</template>

<script>
export default {
  name: "NavItem",
  props: {
    item: {
      type: Object,
      required: true,
    },
    isChild: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isInterior() {
      return !this.isLeaf;
    },
    isLeaf() {
      return (
        this.item.children === undefined || this.item.children.length === 0
      );
    },
  },
};
</script>
