#<<<-----------imports----------->>>
import json, math
import pythoncom
import win32com.client


class AutoCADEngine():

    #<<<-----------init----------->>>
    def __init__(self, ai_output):

        self.ai_output = ai_output

        #<<<-----------connect autocad----------->>>
        pythoncom.CoInitialize()

        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.acad.Visible = True

        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace

        #<<<-----------parse json----------->>>
        self.data = json.loads(self.ai_output)

        #<<<-----------store created entities----------->>>
        self.entities = {}

    #<<<-----------helper----------->>>
    def point(self, x, y, z=0):

        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            (x, y, z)
        )

    #<<<-----------draw rectangle----------->>>
    def draw_rectangle(self, step):

        params = step["parameters"]

        #<<<-----------base point----------->>>
        x1, y1, z1 = params["base_point"]

        x2 = x1 + params["width"]
        y2 = y1 + params["height"]
        z2 = z1

        #<<<-----------rectangle vertices----------->>>
        points = [
            x1, y1,
            x2, y1,
            x2, y2,
            x1, y2
        ]

        #<<<-----------convert to variant----------->>>
        points_variant = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            points
        )

        #<<<-----------create lightweight polyline----------->>>
        pline = self.ms.AddLightWeightPolyline(points_variant)

        #<<<-----------close polyline----------->>>
        pline.Closed = True

        #<<<-----------store entity----------->>>
        self.entities[step["id"]] = pline

    #<<<-----------draw circle----------->>>
    def draw_circle(self, step):

        params = step["parameters"]

        center = self.point(*params["center"])

        radius = params["radius"]

        circle = self.ms.AddCircle(center, radius)

        #<<<-----------store entity----------->>>
        self.entities[step["id"]] = circle
    
        #<<<-----------line----------->>>
    def draw_line(self, step):

        params = step["parameters"]

        start_point = self.point(*params["start_point"])
        end_point = self.point(*params["end_point"])

        line = self.ms.AddLine(start_point, end_point)

        self.entities[step["id"]] = line

    #<<<-----------polyline----------->>>
    def draw_polyline(self, step):

        params = step["parameters"]

        points = []

        for p in params["points"]:
            points.extend([p[0], p[1]])

        points_variant = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            points
        )

        pline = self.ms.AddLightWeightPolyline(points_variant)

        self.entities[step["id"]] = pline

    #<<<-----------arc----------->>>
    def draw_arc(self, step):

        params = step["parameters"]

        start = params["start_point"]
        center = params["center"]
        end = params["end_point"]

        radius = (
            (start[0] - center[0]) ** 2 +
            (start[1] - center[1]) ** 2
        ) ** 0.5

        start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
        end_angle = math.atan2(end[1] - center[1], end[0] - center[0])

        arc = self.ms.AddArc(
            self.point(*center),
            radius,
            start_angle,
            end_angle
        )

        self.entities[step["id"]] = arc

    #<<<-----------polygon----------->>>
    def draw_polygon(self, step):

        params = step["parameters"]

        center = params["center"]
        sides = params["sides"]
        radius = params["radius"]

        self.doc.SendCommand(
            f"_POLYGON {sides} "
            f"{center[0]},{center[1]},{center[2]} "
            f"I {radius} "
        )

    #<<<-----------offset----------->>>
    def offset_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["source"]]

        offset_objs = entity.Offset(params["distance"])

        self.entities[step["id"]] = offset_objs

    #<<<-----------move----------->>>
    def move_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["target"]]

        displacement = params["displacement"]

        entity.Move(
            self.point(0,0,0),
            self.point(*displacement)
        )

    #<<<-----------copy----------->>>
    def copy_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["target"]]

        new_entity = entity.Copy()

        displacement = params["displacement"]

        new_entity.Move(
            self.point(0,0,0),
            self.point(*displacement)
        )

        self.entities[step["id"]] = new_entity

    #<<<-----------rotate----------->>>
    def rotate_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["target"]]

        entity.Rotate(
            self.point(*params["base_point"]),
            math.radians(params["angle"])
        )

    #<<<-----------scale----------->>>
    def scale_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["target"]]

        entity.ScaleEntity(
            self.point(*params["base_point"]),
            params["scale_factor"]
        )

    #<<<-----------mirror----------->>>
    def mirror_entity(self, step):

        params = step["parameters"]

        entity = self.entities[params["target"]]

        p1 = self.point(*params["mirror_line"][0])
        p2 = self.point(*params["mirror_line"][1])

        mirrored = entity.Mirror(p1, p2)

        self.entities[step["id"]] = mirrored

    #<<<-----------text----------->>>
    def draw_text(self, step):

        params = step["parameters"]

        text = self.ms.AddText(
            params["text"],
            self.point(*params["position"]),
            params["height"]
        )

        self.entities[step["id"]] = text

    #<<<-----------extrude----------->>>
    def extrude_entity(self, step):

        params = step["parameters"]

        profile = self.entities[params["profile"]]

        solid = profile.Extrude(
            params["height"]
        )

        self.entities[step["id"]] = solid

    #<<<-----------box----------->>>
    def create_box(self, step):

        params = step["parameters"]

        box = self.ms.AddBox(
            self.point(*params["base_point"]),
            params["length"],
            params["width"],
            params["height"]
        )

        self.entities[step["id"]] = box

    #<<<-----------cylinder----------->>>
    def create_cylinder(self, step):

        params = step["parameters"]

        cylinder = self.ms.AddCylinder(
            self.point(*params["center"]),
            params["radius"],
            params["height"]
        )

        self.entities[step["id"]] = cylinder

    #<<<-----------sphere----------->>>
    def create_sphere(self, step):

        params = step["parameters"]

        sphere = self.ms.AddSphere(
            self.point(*params["center"]),
            params["radius"]
        )

        self.entities[step["id"]] = sphere

    #<<<-----------cone----------->>>
    def create_cone(self, step):

        params = step["parameters"]

        cone = self.ms.AddCone(
            self.point(*params["center"]),
            params["base_radius"],
            params["height"]
        )

        self.entities[step["id"]] = cone

    #<<<-----------torus----------->>>
    def create_torus(self, step):

        params = step["parameters"]

        torus = self.ms.AddTorus(
            self.point(*params["center"]),
            params["major_radius"],
            params["minor_radius"]
        )

        self.entities[step["id"]] = torus

    #<<<-----------wedge----------->>>
    def create_wedge(self, step):

        params = step["parameters"]

        wedge = self.ms.AddWedge(
            self.point(*params["base_point"]),
            params["length"],
            params["width"],
            params["height"]
        )

        self.entities[step["id"]] = wedge

    #<<<-----------execute steps----------->>>
    def execute(self):
        #<<<-----------command handlers----------->>>
        self.command_handlers = {
            "LINE": self.draw_line,
            "PLINE": self.draw_polyline,
            "RECTANG": self.draw_rectangle,
            "CIRCLE": self.draw_circle,
            "ARC": self.draw_arc,
            "POLYGON": self.draw_polygon,
            "OFFSET": self.offset_entity,
            # "TRIM": self.trim_entity,
            # "EXTEND": self.extend_entity,
            "MOVE": self.move_entity,
            "COPY": self.copy_entity,
            "ROTATE": self.rotate_entity,
            "SCALE": self.scale_entity,
            "MIRROR": self.mirror_entity,
            # "ARRAY": self.array_entity,
            # "HATCH": self.hatch_entity,
            "TEXT": self.draw_text,
            "EXTRUDE": self.extrude_entity,
            # "PRESSPULL": self.presspull_entity,
            # "REVOLVE": self.revolve_entity,
            # "SWEEP": self.sweep_entity,
            # "LOFT": self.loft_entity,
            # "UNION": self.union_entities,
            # "SUBTRACT": self.subtract_entities,
            # "INTERSECT": self.intersect_entities,
            # "SLICE": self.slice_entity,
            "BOX": self.create_box,
            "CYLINDER": self.create_cylinder,
            "SPHERE": self.create_sphere,
            "CONE": self.create_cone,
            "TORUS": self.create_torus,
            "WEDGE": self.create_wedge
        }

        #<<<-----------iterate steps----------->>>
        for step in self.data["steps"]:

            action = step["action"]

            #<<<-----------get handler----------->>>
            handler = self.command_handlers.get(action)

            #<<<-----------execute----------->>>
            if handler:
                handler(step)

            #<<<-----------unknown command----------->>>
            else:
                print(f"\nUnknown command: {action}")

        #<<<-----------zoom extents----------->>>
        self.doc.SendCommand("ZOOM E ")

        print("\nDrawing completed successfully.")