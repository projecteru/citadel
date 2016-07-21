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
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        % for pod in pods:
          <tr>
            <td><a href="${url_for('admin.get_pod_nodes', name=pod.name)}">${ pod.name }</a></td>
            <td>${ pod.desc }</td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

</%block>
