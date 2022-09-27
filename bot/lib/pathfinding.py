# TODO: Look into third party library
# TODO: Add failed route lookups to logger
from __future__ import annotations
from ..gameObjects.bounties import solarSystem
import math
from ..cfg import bbData
from typing import Dict, List, Union, cast
from enum import Enum

class AStarRootNode:
    """A node for use in a* pathfinding.
    The root has no parent.

    :var syst: this node's associated solarSystem object.
    :vartype syst: solarSystem
    :var g: The total distance travelled to get to this node
    :vartype g: float
    :var h: The estimated distance from this node to the nearest goal
    :vartype h: float
    :var f: The node's estimated "value" when picking the next node in the route, equal to g + h
    :vartype f: float
    """

    def __init__(self, syst: solarSystem.SolarSystem, g: float = 0, h: float = 0):
        """
        :param solarSystem syst: this node's associated solarSystem object.
        :param float g: The total distance travelled to get to this node (Default 0)
        :param float h: The estimated distance from this node to the nearest goal (Default 0)
        :param float f: The node's estimated "value" when picking the next node in the route, equal to g + h (Default g + h)
        """
        self.syst = syst
        self.g = g
        self.h = h
        self.f = g + h


class AStarNode(AStarRootNode):
    """A node for use in a* pathfinding.

    :var syst: this node's associated solarSystem object.
    :vartype syst: solarSystem
    :var parent: The previous AStarNode in the generated path
    :vartype parent: AStarNode
    :var g: The total distance travelled to get to this node
    :vartype g: float
    :var h: The estimated distance from this node to the nearest goal
    :vartype h: float
    :var f: The node's estimated "value" when picking the next node in the route, equal to g + h
    :vartype f: float
    """

    def __init__(self, syst: solarSystem.SolarSystem, parent: Union[AStarRootNode, "AStarNode"], g: float = 0, h: float = 0):
        """
        :param solarSystem syst: this node's associated solarSystem object.
        :param AStarNode parent: The previous AStarNode in the generated path
        :param float g: The total distance travelled to get to this node (Default 0)
        :param float h: The estimated distance from this node to the nearest goal (Default 0)
        :param float f: The node's estimated "value" when picking the next node in the route, equal to g + h (Default g + h)
        """
        self.parent = parent
        super().__init__(syst, g, h)


def heuristic(start: solarSystem.SolarSystem, end: solarSystem.SolarSystem) -> float:
    """Estimate the distance between two solarSystems, using straight line (pythagorean) distance.

    :param solarSystem start: The system to start calculating distance from
    :param solarSystem end: The system to find distance to
    :return: The straight-line distance from start to end
    """
    return math.sqrt((end.coordinates[1] - start.coordinates[1]) ** 2 \
                    + (end.coordinates[0] - start.coordinates[0]) ** 2)


MAX_ROUTE_LENGTH = 50

class PathfindingError(Enum):
    MAX_LENGTH_REACHED = 1
    NO_ROUTE_FOUND = 2


def bbAStar(start: str, end: str,
        graph: Dict[str, solarSystem.SolarSystem]) -> Union[List[str], PathfindingError]:
    """Find the shortest path from the given start solarSystem to the end solarSystem, using the given graph for edges.
    If no route can be found, the string "! " + start + " -> " + end is returned.
    If the max route length (50) is reached, "#" is returned.

    :param solarSystem start: The starting system for route generation
    :param solarSystem end: The goal system where route generation terminates
    :param dict[str, solarSystem] graph: A dictionary mapping system names to solarSystem objects
    :return: A list containing string system names representing the shortest route from start (the first element) to end
            (the last element)
    :rtype: list
    """

    if start == end:
        return [start]
    
    root = AStarRootNode(graph[start], h=heuristic(graph[start], graph[end]))
    open: List[Union[AStarRootNode, AStarNode]] = [root]
    closed: List[Union[AStarRootNode, AStarNode]] = []
    count = 0

    while open:
        q = open.pop(0)

        count += 1
        if count == MAX_ROUTE_LENGTH:
            return PathfindingError.MAX_LENGTH_REACHED
        for succName in q.syst.getNeighbours():
            if succName == end:
                closed.append(AStarNode(graph[succName], q))
                route = []
                node = closed[-1]
                while node:
                    route.append(node.syst.name)
                    if isinstance(node, AStarRootNode):
                        break
                    node = node.parent
                return route[::-1]

            succ = AStarNode(graph[succName], q)
            succ.g = q.g + 1
            succ.h = heuristic(succ.syst, graph[end])
            succ.f = succ.g + succ.h

            betterFound = False
            for existingNode in open + cast(List[Union[AStarNode, AStarRootNode]], closed):
                if existingNode.syst.coordinates == succ.syst.coordinates and existingNode.f <= succ.f:
                    betterFound = True
            if betterFound:
                continue

            insertPos = len(open)
            for i in range(len(open)):
                if open[i].f > succ.f:
                    if i != 0:
                        insertPos = i - 1
                    break
            open.insert(insertPos, succ)

        closed.append(q)

    return PathfindingError.NO_ROUTE_FOUND


def makeRoute(start: str, end: str) -> Union[List[str], PathfindingError]:
    """Find the shortest route between two systems.

    :param str start: string name of the starting system. Must exist in bbData.builtInSystemObjs
    :param str end: string name of the target system. Must exist in bbData.builtInSystemObjs
    :return: list of string system names where the first element is start, the last element is end,
                and all intermediary systems are adjacent
    :rtype: list[str]
    """
    return bbAStar(start, end, bbData.builtInSystemObjs)
