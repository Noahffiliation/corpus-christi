import {
  getAllSubNodes,
  HierarchyNode,
  GraphNode,
  TreeNode,
  mapTree,
  Group,
  GroupMap,
  Participant,
  GroupObject,
  PersonObject,
  GroupParticipantObject,
  getTree,
  checkConnection,
  HierarchyCycleError,
  isRootNode,
  isOverseer,
  getAllSubGroups,
  getParticipantById,
} from "../../src/models/GroupHierarchyNode";

interface PersonMap {
  [id: number]: PersonObject;
}

declare global {
  namespace jest {
    interface Matchers<R> {
      toContainHierarchyNode(other: HierarchyNode): R;
    }
  }
}

expect.extend({
  toContainHierarchyNode(array: HierarchyNode[], other: HierarchyNode) {
    let index: number = array.findIndex((node) => node.equal(other));
    let pass: boolean, message: () => string;
    if (index === -1) {
      // not found
      pass = false;
      message = () =>
        `There is no hierarchyNode ${other.toString()} in collection ${array.toString()}`;
    } else {
      pass = true;
      message = () =>
        `HierarchyNode ${
          other.toString
        } found at index ${index} in collection ${array.toString()}`;
    }
    return { pass, message };
  },
});

describe("Test case 1, a valid hierarchy structure", () => {
  let groupMap: GroupMap, personMap: PersonMap;
  beforeAll(() => {
    let groupMembers = [
      [1, 1],
      [1, 3],
      [1, 4],
      [2, 2],
      [2, 5],
      [3, 6],
      [3, 2],
      [4, 2],
      [9, 9],
    ];
    let groupManagers = [
      [1, 1],
      [2, 1],
      [3, 1],
      [4, 6],
      [9, 8],
    ];
    ({ groupMap, personMap } = getMap(groupMembers, groupManagers));
  });

  test("hierarchy node subNodes and superNodes functionality", () => {
    let p1: HierarchyNode = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );
    expect(p1.getSubNodes().length).toBe(3);
    expect(p1.getSuperNodes().length).toBe(1);
  });

  test("getAllSubNodes depth filtering", () => {
    let subNodes;
    let p1: HierarchyNode = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );
    // get those only with depth 1
    subNodes = getAllSubNodes(p1, 1, 1);
    expect(subNodes.length).toBe(3);

    let g9: HierarchyNode = new Group(groupMap[9], groupMap);
    // get from depth 1 to depth 2
    subNodes = getAllSubNodes(p1, 1, 2);
    expect(subNodes.length).toBe(9);
    expect(subNodes).not.toContainHierarchyNode(g9);
    expect(subNodes).toContainHierarchyNode(p1);

    // no range
    subNodes = getAllSubNodes(p1);
    expect(subNodes.length).toBe(10);
    expect(subNodes).not.toContainHierarchyNode(g9);
    expect(subNodes).toContainHierarchyNode(p1);
  });

  test("getTree functionality", () => {
    let rootNode;

    // get a tree branching down from Group 3
    rootNode = getTree(new Group(groupMap[3], groupMap));
    expect(rootNode.children.length).toBe(2);
    let p6: HierarchyNode = new Participant(
      { person: personMap[6], active: true },
      groupMap
    );
    let gnp6: GraphNode | undefined = rootNode.children.find((graphNode) =>
      graphNode.hierarchyNode.equal(p6)
    ); // short for: graph node with person 6
    expect(gnp6).not.toBeUndefined();
    expect(gnp6!.children.length).toBe(1);
    let g4: HierarchyNode = new Group(groupMap[4], groupMap);
    let gng4 = gnp6!.children[0];
    expect(gng4.hierarchyNode.equal(g4)).toBe(true);
    expect(gng4.parentPath.length).toBe(2);
  });

  test("getTree cycle handling", () => {
    let p1: HierarchyNode = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );
    let g1: HierarchyNode = new Group(groupMap[1], groupMap);
    let rootNode: GraphNode;
    // get a tree branching down from Person 1
    rootNode = getTree(p1);
    expect(rootNode.children.length).toBe(3);
    let gng1: GraphNode | undefined = rootNode.children.find((graphNode) =>
      graphNode.hierarchyNode.equal(g1)
    );
    // expect Group 1 to be in Person1's children
    expect(gng1).not.toBeUndefined();
    let gnp1: GraphNode | undefined = gng1!.children.find((graphNode) =>
      graphNode.hierarchyNode.equal(p1)
    );
    // expect Person 1 is not rendered again under Group 1
    // (even though Person 1 is both a manager and member of Group 1)
    expect(gnp1).toBeUndefined();
  });

  test("map function on GraphNode", () => {
    interface labeledNode extends TreeNode {
      label?: string;
      children: labeledNode[];
    }
    let rootNode;
    // get a tree branching down from Group 3
    rootNode = getTree(new Group(groupMap[3], groupMap));
    let mappedTreeNode: TreeNode;
    // using customized mapper
    mappedTreeNode = mapTree<GraphNode, TreeNode>(
      rootNode,
      (node) => ({ id: node.id, name: node.name, children: [] }),
      (parentNode, childNode) => {
        parentNode.children.push(childNode);
      }
    );
    expect(mappedTreeNode.children.length).toBe(2);

    let mappedLabeledNode: labeledNode;
    mappedLabeledNode = mapTree(
      rootNode,
      (graphNode) => {
        let mappedNode: labeledNode = { children: [] };
        if (graphNode.hierarchyNode instanceof Group) {
          mappedNode.label = `Group #${
            (graphNode.hierarchyNode.getObject() as GroupObject).id
          }`;
        } else if (graphNode.hierarchyNode instanceof Participant) {
          mappedNode.label = `Person #${
            (graphNode.hierarchyNode.getObject() as GroupParticipantObject)
              .person.id
          }`;
        }
        return mappedNode;
      },
      (parentNode, childNode) => {
        parentNode.children.push(childNode);
      }
    );
    expect(mappedLabeledNode.children.length).toBe(2);
    let p6: labeledNode | undefined = mappedLabeledNode.children.find(
      (child) => child.label === "Person #6"
    );
    expect(p6).not.toBeUndefined();
    expect(p6!.children.length).toBe(1);
    expect(p6!.children[0].label === "Group #4");
  });

  test("checkConnection functionality", () => {
    let p2: Participant = new Participant(
      { person: personMap[2], active: true },
      groupMap
    );
    let g2: Group = new Group(groupMap[2], groupMap);

    // making p2 a manager of g2 should be okay
    expect(() => {
      checkConnection(p2, g2);
    }).not.toThrow();

    let p1: Participant = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );
    let g4: Group = new Group(groupMap[4], groupMap);

    // making p1 a member of g4 should create cycle, because p1 is above g4
    expect(() => {
      checkConnection(g4, p1);
    }).toThrow(HierarchyCycleError);

    // making p2 a leader of g1 should create cycle, because p1 is below g1 but above p2
    let g1: Group = new Group(groupMap[1], groupMap);
    expect(() => {
      checkConnection(p2, g1);
    }).toThrow(`parent ${p2.toString()}`);

    // making p1 a member of g2 should be okay
    expect(() => {
      checkConnection(g2, p1);
    }).not.toThrow();
  });

  test("isRootNode functionality", () => {
    // p1 is a rootNode, because it does not have any super node except itself
    let p1: Participant = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );
    expect(isRootNode(p1)).toBe(true);

    // p8 is a rootNode, because it does not have any super node above it
    let p8: Participant = new Participant(
      { person: personMap[8], active: true },
      groupMap
    );
    expect(isRootNode(p8)).toBe(true);

    // g2 is not a rootNode, because p1 is its parent but not its child
    let g2: Group = new Group(groupMap[2], groupMap);
    expect(isRootNode(g2)).toBe(false);

    // p5 is not a rootNode, because g2 is its parent but not its child
    let p5: Participant = new Participant(
      { person: personMap[5], active: true },
      groupMap
    );
    expect(isRootNode(p5)).toBe(false);
  });

  test("getAllSubGroups/isOverseer functionality", () => {
    let p1: Participant = new Participant(
      { person: personMap[1], active: true },
      groupMap
    );

    // expect person 1 is overseer of group 4
    expect(isOverseer(p1, 4)).toBe(true);

    // expect person 1 is not overseer of group 9
    expect(isOverseer(p1, 9)).toBe(false);

    let p2: Participant = new Participant(
      { person: personMap[2], active: true },
      groupMap
    );

    // expect person 2 is not overseer of group 3
    expect(isOverseer(p2, 3)).toBe(false);

    // expect person 2 has no subgroups
    expect(getAllSubGroups(p2).length).toBe(0);
  });

  test("getParticipantById functionality", () => {
    let p1: Participant | undefined = getParticipantById(1, groupMap);
    expect(p1).not.toBeUndefined();

    // all groups p1 is a member of
    let members = p1!.getObject().person.members;
    expect(members.length).toBe(1);
    expect(members).toContainEqual({ groupId: 1, active: true });

    // all groups p1 is a manager of
    let managers = p1!.getObject().person.managers;
    expect(managers.length).toBe(3);
    expect(managers).toContainEqual({ groupId: 3, active: true });
    expect(managers).not.toContainEqual({ groupId: 6, active: true });
  });
});

describe("Test case 2, a tree that contains cycle", () => {
  let groupMap: GroupMap, personMap: PersonMap;
  beforeAll(() => {
    let groupMembers = [
      [1, 1],
      [2, 3],
    ];
    let groupManagers = [
      [2, 1],
      [1, 2],
      [1, 3],
    ];
    ({ groupMap, personMap } = getMap(groupMembers, groupManagers));
  });

  test("getTree cycle detection", () => {
    let g1: Group = new Group(groupMap[1], groupMap);
    expect(() => getTree(g1)).toThrow("Unexpected cycle in tree");
  });
});

// return an object containing personMap and groupMap
// personMap: { 1: { id: 1, members: [], managers: [{groupId: 1, personId: 1}] } }
// groupMap: { 1: { id: 1, members: [{ groupId: 1, personId: 2, person: {...} }, ...], managers: [...] } }
function getMap(groupMembers: number[][], groupManagers: number[][]) {
  const groupMap: GroupMap = {};
  const personMap: PersonMap = {};
  groupMembers.concat(groupManagers).forEach(([groupId, personId]) => {
    // create active groups
    if (!Object.prototype.hasOwnProperty.call(groupMap, groupId)) {
      groupMap[groupId] = {
        id: groupId,
        members: [],
        managers: [],
        active: true,
      };
    }
    // create persons
    if (!Object.prototype.hasOwnProperty.call(personMap, personId)) {
      personMap[personId] = { id: personId, members: [], managers: [] };
    }
  });

  groupMembers.forEach(([groupId, personId]) => {
    groupMap[groupId].members.push({
      person: personMap[personId],
      active: true,
    });
    personMap[personId].members.push({ groupId, active: true });
  });

  groupManagers.forEach(([groupId, personId]) => {
    groupMap[groupId].managers.push({
      person: personMap[personId],
      active: true,
    });
    personMap[personId].managers.push({ groupId, active: true });
  });

  return { groupMap, personMap };
}