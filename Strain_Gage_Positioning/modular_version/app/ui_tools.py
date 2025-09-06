# File: app/ui_tools.py
"""
Contains reusable UI tool classes that can be attached to a PyVista plotter.
"""
import numpy as np
import pyvista as pv


class DistanceMeasureUI:
    """
    Click two surface points to measure distance.
    Toggle with checkbox or press 'm'. Clear with 'c'.
    """

    def __init__(self, plotter: pv.Plotter, units: str = ""):
        self.pl = plotter
        self.units = units
        self.enabled = False

        # State
        self.picks = []
        self.actors_points = []
        self.actor_line = None
        self.actor_labels = []
        self.actor_text = None

        # Hotkeys (zero-arg callbacks required)
        self.pl.add_key_event("m", lambda: self._on_key_toggle())
        self.pl.add_key_event("c", lambda: self.clear())

        # Helper hint
        self._hint = self.pl.add_text(
            "Distance: off  [M=toggle, C=clear]\nWhen on: click two points on the surface.",
            position="lower_left",
            font_size=6,
        )

    # ---- Public helpers -------------------------------------------------

    def set_units(self, units: str):
        self.units = units
        if len(self.picks) == 2:
            self._update_overlays()

    def enable(self):
        if self.enabled:
            return
        self.enabled = True
        # New API (PyVista >= 0.43): use_picker replaces use_mesh
        try:
            self.pl.enable_point_picking(
                callback=self._on_pick,    # will accept (point, picker)
                use_picker=True,           # snaps using VTK picker
                picker="point",             # snap to surface/cells; try "point" for vertex snap
                show_message=True,
                left_clicking=True,
            )
        except TypeError:
            # Old API fallback
            self.pl.enable_point_picking(
                callback=self._on_pick,    # will accept (point)
                use_mesh=True,             # deprecated, but kept for older versions
                show_message=True,
                left_clicking=True,
            )
        self._update_hint()

    def disable(self):
        if not self.enabled:
            return
        self.enabled = False
        self.pl.disable_picking()
        self._update_hint()

    def clear(self):
        for a in self.actors_points:
            try:
                self.pl.remove_actor(a)
            except Exception:
                pass
        self.actors_points.clear()

        if self.actor_line is not None:
            try:
                self.pl.remove_actor(self.actor_line)
            except Exception:
                pass
            self.actor_line = None

        for a in self.actor_labels:
            try:
                self.pl.remove_actor(a)
            except Exception:
                pass
        self.actor_labels.clear()

        if self.actor_text is not None:
            try:
                self.pl.remove_actor(self.actor_text)
            except Exception:
                pass
            self.actor_text = None

        self.picks.clear()
        self.pl.render()

    # ---- Internal callbacks --------------------------------------------

    def _on_pick(self, point, *_) -> None:
        """Accepts (point) or (point, picker) from PyVista."""
        if not self.enabled:
            return
        if point is None:
            return
        p = np.asarray(point, dtype=float).reshape(3)
        self.picks.append(p)
        if len(self.picks) > 2:
            self.picks = self.picks[-2:]
        self._update_overlays()

    def _on_key_toggle(self):
        new_state = not self.enabled
        if new_state:
            self.enable()
        else:
            self.disable()

    # ---- Drawing / overlays --------------------------------------------

    def _update_overlays(self):
        old = list(self.picks)
        self.clear()
        self.picks = old

        balls, labels = [], []
        color_a = 'cyan'
        color_b = 'magenta'
        if len(self.picks) >= 1:
            balls.append(self._add_point_sphere(self.picks[0]))
            labels.append(self._add_point_label(self.picks[0], "A"))
        if len(self.picks) == 2:
            balls.append(self._add_point_sphere(self.picks[1]))
            labels.append(self._add_point_label(self.picks[1], "B"))
            self._add_line_and_text(self.picks[0], self.picks[1])

        self.actors_points = balls
        self.actor_labels = labels
        self.pl.render()

    def _scene_diag(self):
        try:
            b = self.pl.bounds
            if b is None:
                return None
            return np.linalg.norm([b[1]-b[0], b[3]-b[2], b[5]-b[4]])
        except Exception:
            return None

    def _add_point_sphere(self, p, radius=0.02):
        diag = self._scene_diag()
        if diag is not None:
            radius = max(diag, 1e-9) * 0.01  # 1% scene diagonal
        sph = pv.Sphere(radius=radius, center=p, theta_resolution=24, phi_resolution=24)
        return self.pl.add_mesh(sph, style="surface", opacity=0.8, pickable=False, color='red')

    def _add_point_label(self, p, text):
        return self.pl.add_point_labels(
            [p], [text], point_size=0, font_size=20, shape=None, show_points=False, pickable=False)

    def _add_line_and_text(self, p1, p2):
        line = pv.Line(p1, p2, resolution=1)
        self.actor_line = self.pl.add_mesh(line, line_width=3, pickable=False, color='red')

        d = float(np.linalg.norm(np.asarray(p2) - np.asarray(p1)))
        mid = 0.5 * (np.asarray(p1) + np.asarray(p2))
        label = f"{d:.6g} {self.units}".strip()
        self.actor_text = self.pl.add_point_labels(
            points=[mid],
            labels=[label],
            font_size=24,
            shape='rounded_rect',
            shape_color='green',
            shape_opacity=0.8,
            point_size=0,
            show_points=False,
            pickable=False,
            shadow=True,
            always_visible=True
        )

    def _update_hint(self):
        txt = (
            "Distance: off  [M=toggle, C=clear]\nWhen on: click two points on the surface."
            if self.enabled
            else "Distance: off  [M=toggle, C=clear]\nToggle on, then click two points."
        )
        if self._hint is not None:
            try:
                self.pl.remove_actor(self._hint)
            except Exception:
                pass
        self._hint = self.pl.add_text(txt, position="lower_left", font_size=6)