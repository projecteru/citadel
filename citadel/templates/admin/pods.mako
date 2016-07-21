<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Pod List</%def>

<%block name="main">
  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Pods</h3>
    </%def>
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Hosts</th>
          <th>Share</th>
          <th>Available/Total</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        % for pod in pods:
          <% total, available = pod.get_cores() %>
          <tr>
            <td>${ pod.name }</td>
            <td><a href="${ url_for('admin.get_pod_hosts', name=pod.name) }">${ pod.host_count }</a></td>
            <td>${ '%.1f' % (1.0 / pod.core_share) }</td>
            <td>${ '%.1f / %.1f' % (available, total) }</td>
            <td>${ pod.description }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

</%block>
