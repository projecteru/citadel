<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Node Containers</%def>

<%block name="main">

  <ol class="breadcrumb">
    <li><a href="${ url_for('admin.pods') }">Pod List</a></li>
    <li><a href="${ url_for('admin.get_pod_nodes', name=pod.name) }">Host list of pod <b>${ pod.name }</b></a></li>
    <li class="active">Container list of node <b>${ node.name }</b></li>
  </ol>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Containers</h3>
    </%def>
    ${ utils.container_list(containers) }
  </%call>

</%block>
