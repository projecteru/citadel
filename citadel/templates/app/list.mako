<%inherit file="/base.mako"/>

<%def name="title()">
  Application List
</%def>

<%block name="main">
  <div class="col-md-8 col-md-offset-2">
    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Online Pods</th>
          <th>Online Versions</th>
        </tr>
      </thead>
      <tbody>
        % for app in apps:
          <tr>
            <td><a href="${ url_for('app.get_app', name=app.name) }">${ app.name }</a></td>
            <% containers = app.get_containers(limit=100) %>
            % if containers:
              <td>
                <span class="label label-info">Running</span>
                <span class="label label-success">${ len(containers) } Containers</span>
              </td>
              <td>
                <% pods = set([c.podname for c in containers])%>
                % for p in pods:
                  <span class="label label-info">${ p }</span>
                % endfor
              </td>
              <td>
                <% versions = set([c.version for c in containers])%>
                % for v in versions:
                  <span class="label label-info">${ v }</span>
                % endfor
              </td>
            % else:
              <td><span class="label label-warning">Not running yet</span></td>
              <td><span class="label label-warning">No pods</span></td>
              <td><span class="label label-warning">No versions</span></td>
            % endif
          </tr>
        % endfor
      </tbody>
    </table>
  </div>
</%block>
