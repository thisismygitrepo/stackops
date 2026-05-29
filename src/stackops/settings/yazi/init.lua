-- DuckDB plugin configuration
local duckdb_ok, duckdb = pcall(require, "duckdb")
if duckdb_ok and duckdb and duckdb.setup then
	local setup_ok, setup_err = pcall(function() duckdb:setup() end)
	if not setup_ok then
		ya.err("duckdb.yazi setup failed: " .. tostring(setup_err))
	end
else
	ya.err("duckdb.yazi unavailable: " .. tostring(duckdb))
end

-- https://yazi-rs.github.io/docs/tips#symlink-in-status
-- https://yazi-rs.github.io/docs/tips#user-group-in-status
-- https://yazi-rs.github.io/docs/tips#username-hostname-in-header


Status:children_add(function(self)
	local h = self._current.hovered
	if not h then
		return ""
	end

	local line = ui.Line { " ", ui.Span(tostring(h.url)):fg("cyan") }
	if h.link_to then
		line = line .. ui.Span(" -> " .. tostring(h.link_to)):fg("cyan")
	end

	return line
end, 3300, Status.LEFT)

Status:children_add(function()
	local h = cx.active.current.hovered
	if not h or ya.target_family() ~= "unix" then
		return ""
	end

	return ui.Line {
		ui.Span(ya.user_name(h.cha.uid) or tostring(h.cha.uid)):fg("magenta"),
		ui.Span(":"):fg("magenta"),
		ui.Span(ya.group_name(h.cha.gid) or tostring(h.cha.gid)):fg("magenta"),
		" ",
	}
end, 500, Status.RIGHT)

Header:children_add(function()
	if ya.target_family() ~= "unix" then
		return ""
	end

	return ui.Span(ya.user_name() .. "@" .. ya.host_name() .. ":"):fg("blue")
end, 500, Header.LEFT)
