from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.utils.translation import ungettext_lazy
from django.core import urlresolvers

from django import shortcuts
from django import template
from django.template.defaultfilters import title  # noqa

from horizon.utils import filters

import xmlrpclib

from horizon import tables
from horizon import messages

from openstack_dashboard import policy
from openstack_dashboard import api

from openstack_dashboard.REST.RESTClient import RESTClient
server = RESTClient.getInstance()

class DeleteHACluster(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete HA Cluster",
            u"Delete HA Clusters",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted HA Cluster",
            u"Deleted HA Clusters",
            count
        )
    def handle(self, table, request, obj_ids):
	name = []
	for uuid in obj_ids:
            result = server.delete_cluster(uuid)
	    name.append(self.table.get_object_by_id(uuid).cluster_name) # get cluster's name
	    if result["code"] == "failed":
	        err_msg = result["message"]
	        messages.error(request, err_msg)
	        return False
	success_message = _('Deleted HA Cluster: %s' ) % ",".join(name)
	messages.success(request, success_message)
	return shortcuts.redirect(self.get_success_url(request))

class DeleteComputingNode(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Computing Node",
            u"Delete Computing Nodes",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Computing Node",
            u"Deleted Computing Nodes",
            count
        )


    def handle(self, table, request, obj_ids):
	authUrl = "http://user:0928759204@127.0.0.1:61209"
        #server = xmlrpclib.ServerProxy(authUrl)	
	cluster_id = self.table.kwargs["cluster_id"]
	node_names = []
	for obj_id in obj_ids:
	    node_name = self.table.get_object_by_id(obj_id).computing_node_name
            result = server.delete_node(cluster_id, node_name)
	    node_names.append(node_name)
            if result["code"] == 'failed':
	        err_msg = result["message"]
                messages.error(request, err_msg)
                return False
	self.success_message = _("Deleted Computing Node: %s " % ",".join(node_names))
	messages.success(request, self.success_message)
        return shortcuts.redirect(self.get_success_url(request))

class CreateHAClusterAction(tables.LinkAction):
    name = "create"
    verbose_name = _("Create HA Cluster")
    url = "horizon:haAdmin:ha_clusters:create"
    classes = ("ajax-modal",)
    icon = "plus"

class AddComputingNodeAction(tables.LinkAction):
    name = "add_node"
    verbose_name = _("Add Computing Node")
    url = "horizon:haAdmin:ha_clusters:add_node"
    classes = ("ajax-modal",)
    icon = "plus"

    def get_link_url(self, datum=None):
        cluster_id = self.table.kwargs["cluster_id"]
	print urlresolvers.reverse(self.url,args=[cluster_id])
        return urlresolvers.reverse(self.url, args=[cluster_id])

class ClustersTable(tables.DataTable):
    #message_list = "1234567"
    name = tables.Column("cluster_name",
			 link="horizon:haAdmin:ha_clusters:detail",
 	                 verbose_name=_("Cluster Name"))
    
    computing_number = tables.Column("computing_node_number", verbose_name=_("# of Computing nodes"))

    instance_number = tables.Column("instance_number", verbose_name=_("# of Instances"))
    
    class Meta:
        name = "ha_clusters"
        verbose_name = _("HA_Clusters")
	table_actions = (CreateHAClusterAction, DeleteHACluster)
	row_actions = (DeleteHACluster,)

class ClusterDetailTable(tables.DataTable):

    name = tables.Column("computing_node_name", verbose_name=_("Computing Node Name"))

    instance_number = tables.Column("instance_number", verbose_name=_("# of Instances"))

    class Meta:
	name = "cluster_detail"
	hidden_title = False
	verbose_name = _("Computing Nodes")
        table_actions = (AddComputingNodeAction, DeleteComputingNode) 
	row_actions = (DeleteComputingNode,)

