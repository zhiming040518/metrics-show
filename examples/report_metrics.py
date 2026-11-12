from metrics_show import Event, Metric, MetricsClient


def main():
    with MetricsClient() as client:
        run = client.create_run("image-classification", "sample-baseline")
        client.define_metric(run, Metric(name="epoch", display="value"))
        client.define_metric(run, Metric(name="val/f1", display="both", x="epoch"))
        client.submit(run, [Event(step=1, values={"epoch": 1, "val/f1": 0.84})])
        client.finish(run)
        for event in client.iter_events(run):
            print(event.step, event.values)


if __name__ == "__main__":
    main()
