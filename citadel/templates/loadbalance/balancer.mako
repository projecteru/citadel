<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">Balancer ${ name }</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">${ name }: Instances</h3>
    </%def>

    <table class="table">
      <thead>
        <tr>
          <th>IP</th>
          <th>ContainerID</th>
          <th>Version</th>
          <th>Operations</th>
        </tr>
      </thead>
      <tbody>
        % for elb in elbs:
          <tr>
            <td>
              <a href="javascript://"
                data-placement='right'
                data-toggle="popover"
                rel='popover'
                data-html='true'
                data-original-title='钻进去看看'
                data-content="
                <a href='http://${ elb.ip }/__erulb__/upstream' target='_blank'><span class='label label-info'>upstream</span></a>
                <a href='http://${ elb.ip }/__erulb__/rule' target='_blank'><span class='label label-info'>rule</span></a>
                <br> <br>
                <pre><code style='font-size:70%;white-space:nowrap' >ssh ${ elb.container.nodename } -t 'sudo docker-enter ${ elb.container.short_id }'</code></pre>">
                ${ elb.ip }
              </a>
            </td>
            <td><span class="label label-${'success' if elb.is_alive() else 'danger'}">${ elb.container.short_id }</span></td>
            <td>${ elb.container.short_sha }</td>
            <td><a class="btn btn-xs btn-warning" href="#" data-id="${ elb.id }" name="delete-balancer"><span class="fui-trash"></span> Remove</a></td>
          </tr>
        % endfor
      </tbody>
    </table>
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">${ name }: Domain And Rules</h3>
    </%def>

    <table class="table">
      <thead>
        <tr>
          <th>Domain</th>
          <th>App</th>
          <th>Operations</th>
        </tr>
      </thead>
      <tbody>
        % for rule in rules:
          <tr id="${ rule.domain }">
            <td><a href="http://${ rule.domain }" target="_blank">${ rule.domain }</a></td>
            <td><a target="_blank" href="${ url_for('app.app', name=rule.appname) }">${ rule.appname }</a></td>
            <td>
              <a class="btn btn-xs btn-info" href="${ url_for('loadbalance.edit_rule', name=name, domain=rule.domain) }", name="edit-rule">Edit</a>
              <a name="delete-rule" class="btn btn-xs btn-warning" data-rule-domain="${ rule.domain }" data-elbname="${ name }"><span class="fui-trash"></span></a>
            </td>
          </tr>
        % endfor
      </tbody>
    </table>

  </%call>

  <ul class="nav nav-tabs" id="add-rule-form">
    <li role="presentation" class="active"><a class="btn" data-target="#add-general-rule" data-toggle="tab"> Simple </a></li>
    <li role="presentation"><a class="btn" data-target="#add-rule" data-toggle="tab"> Advanced </a></li>
  </ul>

  <div class="tab-content">

    <br>

    <div class="col-md-8 col-md-offset-2 tab-pane active" id="add-general-rule">
      <form class="form-horizontal" action="${ url_for('loadbalance.add_general_rule', name=name) }" method="POST">
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">App Name</label>
          <div class="col-sm-10">
            <select id="" class="form-control" name="appname">
              % for app in all_apps:
                <option value="${ app.name }">${ app.name }</option>
              % endfor
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">Entrypoint</label>
          <div class="col-sm-10">
            <select id="" class="form-control" name="entrypoint">
              <option value="_all">_all</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">Podname</label>
          <div class="col-sm-10">
            <% pods = all_apps[0].get_online_pods() %>
            <select id="" class="form-control" name="podname">
              % for p in pods:
                <option value="${ p }">${ p }</option>
              % endfor
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">Domain</label>
          <div class="col-sm-10">
            <span data-toggle="tooltip" data-placement="top" title="带不带http://都可以的，我会帮你清理">
              <input class="form-control" type="text" name="domain" placeholder="比如 http://ci-test.test.ricebook.net 或者 ci-test.test.ricebook.net">
            </span>
          </div>
        </div>
        <div class="form-group">
          <div class="col-sm-10 col-sm-offset-2">
            <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
          </div>
        </div>
      </form>
    </div>

    <div class="col-md-8 col-md-offset-2 tab-pane" id="add-rule">
      <form class="form-horizontal" action="${ url_for('loadbalance.add_rule', name=name) }" method="POST">
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">App Name</label>
          <div class="col-sm-10">
            <select id="" class="form-control" name="appname">
              % for app in all_apps:
                <option value="${ app.name }">${ app.name }</option>
              % endfor
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">Domain</label>
          <div class="col-sm-10">
            <span data-toggle="tooltip" data-placement="top" title="带不带http://都可以的，我会帮你清理">
              <input class="form-control" type="text" name="domain">
            </span>
          </div>
        </div>
        <div class="form-group">
          <label class="col-sm-2 control-label" for="">Rule</label>
          <div class="col-sm-10">
            <input class="form-control" type="text" name="rule">
          </div>
        </div>
        <div class="form-group">
          <div class="col-sm-10 col-sm-offset-2">
            <button class="btn btn-info" type="submit"><span class="fui-plus"></span> Add</button>
          </div>
        </div>
      </form>
    </div>

  </div>

</%block>

<%def name="bottom_script()">
  <script>
    $(function(){
      $('[data-toggle="tooltip"]').tooltip();
    });
  </script>
  <script src="/citadel/static/js/balancer.js" type="text/javascript"></script>
  <script src="/citadel/static/js/add-loadbalance.js" type="text/javascript"></script>
</%def>
