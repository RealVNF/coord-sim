
class Placement:

    @staticmethod
    def calculate_demand(flow, sf, available_sf, service_functions):
        """
        Calculate the demanded capacity when the flow is processed at this node. Report if the VNF/SF needs to be
        placed
        """

        if sf in available_sf:
            vnf_need_placement = False
            demanded_total_capacity = 0.0
            for sf_i, sf_data in available_sf.items():
                if sf == sf_i:
                    # Include flows data rate in requested sf capacity calculation
                    demanded_total_capacity += service_functions[sf_i]['resource_function'](
                        sf_data['load'] + flow.dr)
                else:
                    demanded_total_capacity += service_functions[sf_i]['resource_function'](sf_data['load'])
            return demanded_total_capacity, vnf_need_placement
        else:
            vnf_need_placement = True
            available_sf[sf] = {'load': 0.0}
            demanded_total_capacity = 0.0
            for sf_i, sf_data in available_sf.items():
                if sf == sf_i:
                    # Include flows data rate in requested sf capacity calculation
                    demanded_total_capacity += service_functions[sf_i]['resource_function'](
                        sf_data['load'] + flow.dr)
                else:
                    demanded_total_capacity += service_functions[sf_i]['resource_function'](sf_data['load'])
            del available_sf[sf]
            return demanded_total_capacity, vnf_need_placement

    @staticmethod
    def remove_unused_sf(node_id, available_sf, placement):
        for sf, sf_data in available_sf.items():
            if sf_data['load'] == 0:
                placement[node_id].remove(sf)