#!/usr/bin/env python

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'ament', 'ament_tools'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'ament', 'ament_package'))

from ament_tools.packages import find_unique_packages

import pygraphviz


def main(group_by_path=True, tred=False):
    pkgs = find_unique_packages('src')
    pkgs_by_name = dict([(pkg.name, pkg) for pkg_path, pkg in pkgs.items()
                         # if 'connext' not in pkg.name and 'ament' not in pkg.name])
                         if 'ament' not in pkg.name])
    pkg_names = pkgs_by_name.keys()

    graph = pygraphviz.AGraph(directed=True, strict=False)  # , concentrate=True)

    # add all packages as nodes
    for pkg_name in sorted(pkg_names):
        graph.add_node(pkg_name)

    # group packages by parent folder
    groups = {}
    for pkg_path, pkg in pkgs.items():
        parent_path = os.path.dirname(pkg_path)
        if parent_path not in groups:
            groups[parent_path] = []
        groups[parent_path].append(pkg.name)

    # collect all dependencies by type
    # and add edges for them
    build_depends = {}
    run_depends = {}
    test_depends = {}
    for pkg_name in sorted(pkg_names):
        pkg = pkgs_by_name[pkg_name]
        build_depends[pkg_name] = set([])
        for dep in pkg.build_depends + pkg.buildtool_depends:
            if dep.name in pkg_names and dep.name not in build_depends[pkg_name]:
                build_depends[pkg_name].add(dep.name)

        run_depends[pkg_name] = set([])
        for dep in pkg.build_export_depends + pkg.buildtool_export_depends + pkg.exec_depends:
            if dep.name in pkg_names and dep.name not in run_depends[pkg_name]:
                run_depends[pkg_name].add(dep.name)

        test_depends[pkg_name] = set([])
        for dep in pkg.test_depends:
            if dep.name in pkg_names and dep.name not in test_depends[pkg_name]:
                test_depends[pkg_name].add(dep.name)

    # add edges using parallel splines instead of separately routed multiedges
    for pkg_name in sorted(set(build_depends.keys()) | set(run_depends.keys()) | set(test_depends.keys())):
        build_deps = set(build_depends.get(pkg_name, []))
        run_deps = set(run_depends.get(pkg_name, []))
        test_deps = set(test_depends.get(pkg_name, []))
        # for dep in sorted(build_deps | run_deps | test_deps):
        for dep in sorted(build_deps | run_deps):
            colors = []
            if dep in build_deps:
                colors.append('red')
            if dep in run_deps:
                colors.append('darkgreen')
            # if dep in test_deps:
            #     colors.append('blue3')
            graph.add_edge(pkg_name, dep, color=':'.join(colors))

    print(graph.to_string())

    # add subgraphs based on rank
    if not group_by_path:
        depends = {}
        for pkg in pkgs.values():
            depends[pkg.name] = build_depends[pkg.name] | run_depends[pkg.name] | test_depends[pkg.name]
        rank = 1
        while depends:
            leafs = [pkg_name for pkg_name, deps in depends.items() if not deps]
            for leaf in leafs:
                del depends[leaf]
            for deps in depends.values():
                deps -= set(leafs)
            graph.add_subgraph(sorted(leafs), name='r%d' % rank, rank='same')
            rank += 1

    # add subgraphs based on grouping
    if group_by_path:
        attributes = {
            'color': 'gray',
            'fontcolor': 'gray',
            'style': 'bold',
            'weight': 0,
        }
        i = 0
        for parent_path, pkg_names in groups.items():
            i += 1
            attributes.update({
                'label': parent_path,
            })

            # prevent edges to be duplicated inside subgraph
            edges_func = graph.edges

            def empty(*args, **kwargs):
                return []
            graph.edges = empty

            # subgraph = graph.add_subgraph(
            graph.add_subgraph(
                nbunch=pkg_names, name='cluster%d' % i, **attributes)

            graph.edges = edges_func

    if tred:
        # all_edges = graph.edges()
        # remove transitive dependencies
        graph.tred()
    graph.layout('dot')
    # if tred:
    #     # readd transitive dependencies after layout
    #     for edge in all_edges:
    #         if not graph.has_edge(edge):
    #             graph.add_edge(edge)

    graph.draw('ament_graph.png')


if __name__ == '__main__':
    main()
