#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import argparse
import os
import libcst as cst
import pathlib
import sys
from typing import (Any, Callable, Dict, List, Sequence, Tuple)


def partition(
    predicate: Callable[[Any], bool],
    iterator: Sequence[Any]
) -> Tuple[List[Any], List[Any]]:
    """A stable, out-of-place partition."""
    results = ([], [])

    for i in iterator:
        results[int(predicate(i))].append(i)

    # Returns trueList, falseList
    return results[1], results[0]


class securesourcemanagerCallTransformer(cst.CSTTransformer):
    CTRL_PARAMS: Tuple[str] = ('retry', 'timeout', 'metadata')
    METHOD_TO_PARAMS: Dict[str, Tuple[str]] = {
        'batch_create_pull_request_comments': ('parent', 'requests', ),
        'close_issue': ('name', 'etag', ),
        'close_pull_request': ('name', ),
        'create_branch_rule': ('parent', 'branch_rule', 'branch_rule_id', ),
        'create_hook': ('parent', 'hook', 'hook_id', ),
        'create_instance': ('parent', 'instance_id', 'instance', 'request_id', ),
        'create_issue': ('parent', 'issue', ),
        'create_issue_comment': ('parent', 'issue_comment', ),
        'create_pull_request': ('parent', 'pull_request', ),
        'create_pull_request_comment': ('parent', 'pull_request_comment', ),
        'create_repository': ('parent', 'repository', 'repository_id', ),
        'delete_branch_rule': ('name', 'allow_missing', ),
        'delete_hook': ('name', ),
        'delete_instance': ('name', 'request_id', ),
        'delete_issue': ('name', 'etag', ),
        'delete_issue_comment': ('name', ),
        'delete_pull_request_comment': ('name', ),
        'delete_repository': ('name', 'allow_missing', ),
        'fetch_blob': ('repository', 'sha', ),
        'fetch_tree': ('repository', 'ref', 'recursive', 'page_size', 'page_token', ),
        'get_branch_rule': ('name', ),
        'get_hook': ('name', ),
        'get_iam_policy_repo': ('resource', 'options', ),
        'get_instance': ('name', ),
        'get_issue': ('name', ),
        'get_issue_comment': ('name', ),
        'get_pull_request': ('name', ),
        'get_pull_request_comment': ('name', ),
        'get_repository': ('name', ),
        'list_branch_rules': ('parent', 'page_size', 'page_token', ),
        'list_hooks': ('parent', 'page_size', 'page_token', ),
        'list_instances': ('parent', 'page_size', 'page_token', 'filter', 'order_by', ),
        'list_issue_comments': ('parent', 'page_size', 'page_token', ),
        'list_issues': ('parent', 'page_size', 'page_token', 'filter', ),
        'list_pull_request_comments': ('parent', 'page_size', 'page_token', ),
        'list_pull_request_file_diffs': ('name', 'page_size', 'page_token', ),
        'list_pull_requests': ('parent', 'page_size', 'page_token', ),
        'list_repositories': ('parent', 'page_size', 'page_token', 'filter', 'instance', ),
        'merge_pull_request': ('name', ),
        'open_issue': ('name', 'etag', ),
        'open_pull_request': ('name', ),
        'resolve_pull_request_comments': ('parent', 'names', 'auto_fill', ),
        'set_iam_policy_repo': ('resource', 'policy', 'update_mask', ),
        'test_iam_permissions_repo': ('resource', 'permissions', ),
        'unresolve_pull_request_comments': ('parent', 'names', 'auto_fill', ),
        'update_branch_rule': ('branch_rule', 'update_mask', 'validate_only', ),
        'update_hook': ('update_mask', 'hook', ),
        'update_issue': ('issue', 'update_mask', ),
        'update_issue_comment': ('issue_comment', 'update_mask', ),
        'update_pull_request': ('pull_request', 'update_mask', ),
        'update_pull_request_comment': ('pull_request_comment', 'update_mask', ),
        'update_repository': ('repository', 'update_mask', 'validate_only', ),
    }

    def leave_Call(self, original: cst.Call, updated: cst.Call) -> cst.CSTNode:
        try:
            key = original.func.attr.value
            kword_params = self.METHOD_TO_PARAMS[key]
        except (AttributeError, KeyError):
            # Either not a method from the API or too convoluted to be sure.
            return updated

        # If the existing code is valid, keyword args come after positional args.
        # Therefore, all positional args must map to the first parameters.
        args, kwargs = partition(lambda a: not bool(a.keyword), updated.args)
        if any(k.keyword.value == "request" for k in kwargs):
            # We've already fixed this file, don't fix it again.
            return updated

        kwargs, ctrl_kwargs = partition(
            lambda a: a.keyword.value not in self.CTRL_PARAMS,
            kwargs
        )

        args, ctrl_args = args[:len(kword_params)], args[len(kword_params):]
        ctrl_kwargs.extend(cst.Arg(value=a.value, keyword=cst.Name(value=ctrl))
                           for a, ctrl in zip(ctrl_args, self.CTRL_PARAMS))

        request_arg = cst.Arg(
            value=cst.Dict([
                cst.DictElement(
                    cst.SimpleString("'{}'".format(name)),
cst.Element(value=arg.value)
                )
                # Note: the args + kwargs looks silly, but keep in mind that
                # the control parameters had to be stripped out, and that
                # those could have been passed positionally or by keyword.
                for name, arg in zip(kword_params, args + kwargs)]),
            keyword=cst.Name("request")
        )

        return updated.with_changes(
            args=[request_arg] + ctrl_kwargs
        )


def fix_files(
    in_dir: pathlib.Path,
    out_dir: pathlib.Path,
    *,
    transformer=securesourcemanagerCallTransformer(),
):
    """Duplicate the input dir to the output dir, fixing file method calls.

    Preconditions:
    * in_dir is a real directory
    * out_dir is a real, empty directory
    """
    pyfile_gen = (
        pathlib.Path(os.path.join(root, f))
        for root, _, files in os.walk(in_dir)
        for f in files if os.path.splitext(f)[1] == ".py"
    )

    for fpath in pyfile_gen:
        with open(fpath, 'r') as f:
            src = f.read()

        # Parse the code and insert method call fixes.
        tree = cst.parse_module(src)
        updated = tree.visit(transformer)

        # Create the path and directory structure for the new file.
        updated_path = out_dir.joinpath(fpath.relative_to(in_dir))
        updated_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate the updated source file at the corresponding path.
        with open(updated_path, 'w') as f:
            f.write(updated.code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Fix up source that uses the securesourcemanager client library.

The existing sources are NOT overwritten but are copied to output_dir with changes made.

Note: This tool operates at a best-effort level at converting positional
      parameters in client method calls to keyword based parameters.
      Cases where it WILL FAIL include
      A) * or ** expansion in a method call.
      B) Calls via function or method alias (includes free function calls)
      C) Indirect or dispatched calls (e.g. the method is looked up dynamically)

      These all constitute false negatives. The tool will also detect false
      positives when an API method shares a name with another method.
""")
    parser.add_argument(
        '-d',
        '--input-directory',
        required=True,
        dest='input_dir',
        help='the input directory to walk for python files to fix up',
    )
    parser.add_argument(
        '-o',
        '--output-directory',
        required=True,
        dest='output_dir',
        help='the directory to output files fixed via un-flattening',
    )
    args = parser.parse_args()
    input_dir = pathlib.Path(args.input_dir)
    output_dir = pathlib.Path(args.output_dir)
    if not input_dir.is_dir():
        print(
            f"input directory '{input_dir}' does not exist or is not a directory",
            file=sys.stderr,
        )
        sys.exit(-1)

    if not output_dir.is_dir():
        print(
            f"output directory '{output_dir}' does not exist or is not a directory",
            file=sys.stderr,
        )
        sys.exit(-1)

    if os.listdir(output_dir):
        print(
            f"output directory '{output_dir}' is not empty",
            file=sys.stderr,
        )
        sys.exit(-1)

    fix_files(input_dir, output_dir)
