# """cli for scheduler
# """

# from stackops.utils.scheduling import PathExtended, Report, DEFAULT_CONFIG, read_task_from_dir, main

# def main_parse():
#     print("\n" + "=" * 50)
#     print("📅 Welcome to the Scheduler CLI")
#     print("=" * 50 + "\n")

#     parser = argparse.ArgumentParser(description='Run tasks.')
#     parser.add_argument('root', type=str, default=None, help='📁 Root directory of tasks.')
#     parser.add_argument('--ignore_conditions', "-i", action='store_true', help='🚫 Ignore conditions for running tasks.', default=False)
#     parser.add_argument('--report', "-R", action='store_true', help='📊 Print report.', default=False)
#     parser.add_argument('--create_task', "-c", action='store_true', help='🆕 Add default config.', default=False)
#     args = parser.parse_args()

#     tmp = PathExtended(args.root).expanduser().absolute()
#     if PathExtended(args.root).joinpath(".scheduler").exists():
#         root = PathExtended(args.root).joinpath(".scheduler")
#     elif tmp.name == ".scheduler":
#         root = tmp
#     else:
#         root = tmp.joinpath(".scheduler")
#         root.mkdir(parents=True, exist_ok=True)

#     print(f"\n✅ Running tasks in {root}\n")

    # if args.report:
    #     print("📊 Generating report...")
    #     reports: list[Report] = [Report.from_path(read_task_from_dir(x).report_path) for x in PathExtended(root).glob("*")]

        # Format as markdown table
#         report_data = [r.__dict__ for r in reports]
#         if report_data:
#             # Get keys from first report
#             keys = list(report_data[0].keys())
#             # Create header
#             header = "|" + "|".join(f" {key} " for key in keys) + "|"
#             separator = "|" + "|".join(" --- " for _ in keys) + "|"
#             # Create rows
#             rows = []
#             for report in report_data:
#                 row_values = [f" {str(report.get(key, ''))} " for key in keys]
#                 rows.append("|" + "|".join(row_values) + "|")
#             markdown_table = "\n".join([header, separator] + rows)
#             print(markdown_table)
#         else:
#             print("No reports found.")
#         print("\n✅ Report generated successfully!\n")
#         return None

#     if args.create_task:
#         task_name = input("📝 Enter task name: ")
#         task_root = root.joinpath(task_name)
#         task_root.mkdir(parents=True, exist_ok=False)
#         task_root.joinpath("config.ini").write_text(DEFAULT_CONFIG, encoding="utf-8")
#         task_root.joinpath("task.py").write_text("""
# # Scheduler Task.
# """)
#         print(f"\n✅ Task '{task_name}' created in {task_root}. Head there and edit the config.ini file & task.py file.\n")
#         return None

#     print("🚀 Executing tasks...")
#     main(root=str(root), ignore_conditions=args.ignore_conditions)
#     print("🎉 All tasks executed successfully!\n")

# if __name__ == "__main__":
#     main_parse()
