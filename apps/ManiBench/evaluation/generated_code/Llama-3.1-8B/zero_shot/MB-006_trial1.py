class Histogram(VGroup):
    def __init__(self, samples, x_min, x_max, x_range, y_range, x_axis_label, y_axis_label, title):
        super().__init__()
        self.x_min = x_min
        self.x_max = x_max
        self.x_range = x_range
        self.y_range = y_range
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.title = title
        self.add(self.create_histogram(samples))

    def create_histogram(self, samples):
        bars = VGroup()
        for i in range(self.x_range):
            bar = Rectangle(width=1, height=samples[i] / self.y_range, color=WHITE)
            bars.add(bar)
        x_axis = Line(start=[-self.x_range/2, 0], end=[self.x_range/2, 0], color=WHITE)
        y_axis = Line(start=[0, -self.y_range/2], end=[0, self.y_range/2], color=WHITE)
        x_axis_label = Text(self.x_axis_label).scale(0.5).next_to(x_axis, RIGHT)
        y_axis_label = Text(self.y_axis_label).scale(0.5).next_to(y_axis, LEFT)
        title = Text(self.title).scale(0.8).to_edge(UP)
        self.add(x_axis, y_axis, x_axis_label, y_axis_label, title)
        return bars

class NormalDistribution(VGroup):
    def __init__(self, x_min, x_max, x_range, y_range, x_axis_label, y_axis_label, title):
        super().__init__()
        self.x_min = x_min
        self.x_max = x_max
        self.x_range = x_range
        self.y_range = y_range
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.title = title
        self.add(self.create_normal_distribution())

    def create_normal_distribution(self):
        x_values = np.linspace(self.x_min, self.x_max, self.x_range)
        y_values = np.exp(-((x_values - 0) ** 2) / (2 * 1 ** 2)) / (1 * np.sqrt(2 * np.pi))
        bars = VGroup()
        for i in range(self.x_range):
            bar = Rectangle(width=1, height=y_values[i] / self.y_range, color=WHITE)
            bars.add(bar)
        x_axis = Line(start=[-self.x_range/2, 0], end=[self.x_range/2, 0], color=WHITE)
        y_axis = Line(start=[0, -self.y_range/2], end=[0, self.y_range/2], color=WHITE)
        x_axis_label = Text(self.x_axis_label).scale(0.5).next_to(x_axis, RIGHT)
        y_axis_label = Text(self.y_axis_label).scale(0.5).next_to(y_axis, LEFT)
        title = Text(self.title).scale(0.8).to_edge(UP)
        self.add(x_axis, y_axis, x_axis_label, y_axis_label, title)
        return bars