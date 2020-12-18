"""
 Copyright (C) 2018-2020 Intel Corporation

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""
import numpy as np

from typing import Dict

from mo.front.tf.graph_utils import create_op_with_const_inputs
from mo.graph.graph import Graph, Node
from mo.middle.replacement import MiddleReplacementPattern
from mo.ops.broadcast import Broadcast


class RandomUniformReplacer(MiddleReplacementPattern):
    """
    TODO: fix this transformation because it is not valid for some cases
    Replaces RandomUniform operation with Broadcast of ones in sub-graph:

    ShapeOf ---> RandomUniform ---> Mul

    """

    enabled = True

    @staticmethod
    def pattern():
        return dict(
            nodes=[
                ('shape', dict(op='ShapeOf')),
                ('shape_data', dict()),
                ('random_uniform', dict(op='RandomUniform')),
                ('random_uniform_data', dict()),
                ('mul', dict(op='Mul')),
                ('mul_const', dict(op='Const')),
                ('mul_const_data', dict())
            ],
            edges=[
                ('shape', 'shape_data'),
                ('shape_data', 'random_uniform'),
                ('random_uniform', 'random_uniform_data'),
                ('random_uniform_data', 'mul'),
                ('mul_const', 'mul_const_data'),
                ('mul_const_data', 'mul')
            ]
        )

    @staticmethod
    def replace_pattern(graph: Graph, match: Dict[str, Node]):
        node = match['random_uniform']
        node_name = node.soft_get('name', node.id)
        data_type = match['mul_const'].out_port(0).get_data_type()
        broadcast_node = create_op_with_const_inputs(graph, Broadcast, port_value_dict={0: np.array([1], dtype=data_type)},
                                                     op_attrs={'name': node_name + '/Broadcast', 'mode': 'numpy'})
        node.in_port(0).get_connection().set_destination(broadcast_node.in_port(1))
        node.out_port(0).get_connection().set_source(broadcast_node.out_port(0))


class RandomUniformReplacer2(MiddleReplacementPattern):
    """
    Dropout (for inference mode) containing RandomUniform can be replaced with Broadcast of ones in sub-graph.
    """
    enabled = True

    def run_before(self):
        return [RandomUniformReplacer]

    @staticmethod
    def pattern():
        return dict(
            nodes=[
                ('shape', dict(op='ShapeOf')),
                ('shape_data', dict()),
                ('random_uniform', dict(op='RandomUniform')),
                ('random_uniform_data', dict()),
                ('mul', dict(op='Mul')),
                ('mul_data', dict()),
                ('mul_const', dict(op='Const')),
                ('mul_const_data', dict()),
                ('add', dict(op='Add')),
                ('add_data', dict()),
                ('add_const', dict(op='Const')),
                ('add_const_data', dict()),
                ('add2', dict(op='Add')),
                ('add2_data', dict()),
                ('add2_const', dict(op='Const')),
                ('add2_const_data', dict()),
                ('floor', dict(op='Floor')),
            ],
            edges=[
                ('shape', 'shape_data'),
                ('shape_data', 'random_uniform'),
                ('random_uniform', 'random_uniform_data'),
                ('random_uniform_data', 'mul'),
                ('mul_const', 'mul_const_data'),
                ('mul_const_data', 'mul'),
                ('mul', 'mul_data'),
                ('add_const', 'add_const_data'),
                ('add_const_data', 'add'),
                ('mul_data', 'add'),
                ('add2_const', 'add2_const_data'),
                ('add2_const_data', 'add2'),
                ('add_data', 'add2'),
                ('add2_data', 'floor'),
            ]
        )

    @staticmethod
    def replace_pattern(graph: Graph, match: Dict[str, Node]):
        ru_node = match['random_uniform']
        ru_node_name = ru_node.soft_get('name', ru_node.id)
        floor_node = match['floor']
        data_type = match['mul_const'].out_port(0).get_data_type()
        broadcast_node = create_op_with_const_inputs(graph, Broadcast, port_value_dict={0: np.array([1], dtype=data_type)},
                                                     op_attrs={'name': ru_node_name + '/Broadcast', 'mode': 'numpy'})
        ru_node.in_port(0).get_connection().set_destination(broadcast_node.in_port(1))
        floor_node.out_port(0).get_connection().set_source(broadcast_node.out_port(0))

        # to avoid re-inference of shape and touching in next replacements
        graph.remove_node(ru_node.id)
        graph.remove_node(floor_node.id)
