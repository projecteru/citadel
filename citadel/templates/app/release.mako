<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ release.name } @ ${ release.sha[:7] }
</%def>

<%def name="more_css()">
  .progress-bar {
  -webkit-transition: none !important;
  transition: none !important;
  }
</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Release</h3>
    </%def>
    <h4><a href="${ url_for('app.get_app', name=app.name) }">${ app.name }</a> @ ${ release.short_sha }</h4>
    <p>image: ${ release.image }</p>
    % if release.image:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Container
      </button>
    % elif g.user.privilege:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Raw Container
      </button>
    % else:
      <button class="btn btn-info pull-right" disabled>
        <span class="fui-plus"></span> Add Container
      </button>
    % endif
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">app.yaml</h3>
    </%def>

    <pre>${ appspecs | n }</pre>
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    <%utils:container_list containers="${ containers }">
    </%utils:container_list>
  </%call>

</%block>

<%def name="more_body()">

  <%call expr="utils.modal('add-container-modal')">

    <%def name="header()">
      <h3 class="modal-title">Add Container</h3>
    </%def>

    <form id="add-container-form" class="form-horizontal" action="">
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">Release</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="release" value="${release.name} / ${release.short_sha}" data-id="${release.id}" disabled>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Pod</label>
        <div class="col-sm-10">
          <select name="pod" class="form-control">
            % for p in pods:
              <option value="${ p.name }">${ p.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">Node</label>
        <div class="col-sm-10">
          <select class="form-control" name="node">
            % if len(nodes) > 1:
              <option value="_random">Let Eru choose for me</option>
            % endif
            % for n in nodes:
              <option value="${ n.name }">${ n.name }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Entrypoint</label>
        <div class="col-sm-10">
          <select class="form-control" name="entrypoint">
            % for entry in release.specs.entrypoints.keys():
              <option value="${ entry }">${ entry }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Env</label>
        <div class="col-sm-10">
          <select class="form-control" name="envname">
            % for env in envs:
              <option value="${ env.envname }">${ env.envname }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">几个？</label>
        <div class="col-sm-10">
          <input class="form-control" type="number" name="count" value="1">
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">CPU</label>
        <div class="col-sm-10">
          <select class="form-control" name="cpu">
            % for cpu_value in (0.5, 1, 2, 4, 8):
              <option value="${ cpu_value }" type="number">${ cpu_value }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">Memory</label>
        <div class="col-sm-10">
          <select class="form-control" name="memory">
            % for memory_value in ('512MB', '1GB', '2GB', '4GB', '8GB', '16GB'):
              <option value="${ memory_value }">${ memory_value }</option>
            % endfor
          </select>
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">Extra Env</label>
        <div class="col-sm-10">
          <input class="form-control" type="text" name="envs" value="" placeholder="例如a=1;b=2;">
        </div>
      </div>
      <div class="form-group">
        <label class="col-sm-2 control-label" for="">Network</label>
        <div class="col-sm-10" id="network-checkbox">
          % for network in networks:
            <label class="checkbox" for="">
              <input type="checkbox" name="network" value="${ network.name }" checked>${ network.name } -
              % for cidr in network.subnets:
                <span class="label label-info">${ cidr }</span>
              % endfor
            </label>
          % endfor
        </div>
      </div>
      <div class="form-group collapse advance-form-group">
        <label class="col-sm-2 control-label" for="">Debug</label>
        <div class="col-sm-10">
          <input class="form-control" type="checkbox" name="debug" value="">
        </div>
      </div>
      % if g.user.privilege:
        <div class="form-group collapse advance-form-group">
          <label class="col-sm-2 control-label" for="">Raw</label>
          <div class="col-sm-10">
            <input class="form-control" type="checkbox" name="raw" value="">
          </div>
        </div>
      % endif
    </form>

    <%def name="footer()">
      <button class="btn btn-warning pull-left" data-toggle="collapse" data-target=".advance-form-group">老子搞点高级的</button>
      <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
      <button class="btn btn-info" id="add-container-button"><span class="fui-plus"></span>Go</button>
    </%def>

  </%call>

  <%call expr="utils.modal('container-progress')">
    <%def name="header()">
      <h3 class="modal-title">Please wait...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <div class="progress">
      <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="100" aria-valuemin="0" aira-valuemax="100">
        <span class="sr-only">Waiting ...</span>
      </div>
    </div>
  </%call>

</%def>

<%def name="bottom_script()">
  <script src="/citadel/static/js/deploy.js" type="text/javascript"></script>
</%def>
