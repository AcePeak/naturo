/*
 * Naturo owned Java Swing recognition fixture (issue #932).
 *
 * A deliberately small, self-contained Swing application that exposes a known
 * set of accessible controls — buttons, a text field, a checkbox, a label, a
 * table and a tree. It exists to prove naturo's Java Access Bridge (JAB)
 * recognition against ground truth: the Windows UI Automation tree collapses a
 * Swing window into opaque window chrome, while JAB recovers every control
 * below.
 *
 * The control names are stable and unique so tests can assert exact ground
 * truth. The window title is also stable so the harness can locate the window.
 *
 * Build and run with the JDK directly — no Maven/Gradle required:
 *
 *     javac SwingControlsFixture.java
 *     java  SwingControlsFixture
 *
 * Java Access Bridge must be enabled for naturo to see the controls
 * (`jabswitch -enable`, then restart the JVM).
 */
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.JTree;
import javax.swing.SwingUtilities;
import javax.swing.WindowConstants;
import javax.swing.table.DefaultTableModel;
import javax.swing.tree.DefaultMutableTreeNode;
import java.awt.BorderLayout;
import java.awt.GridLayout;

public final class SwingControlsFixture {

    /** Stable window title used by the recognition harness to find this window. */
    public static final String WINDOW_TITLE = "Naturo Swing Recognition Fixture";

    /** Initial status-label text (and accessible name) before any action. */
    public static final String STATUS_PENDING = "Order Status: Pending";
    /** Status after the Submit Order button is actuated — the success-action proof. */
    public static final String STATUS_SUBMITTED = "Order Status: Submitted";
    /** Status after the Cancel Order button is actuated. */
    public static final String STATUS_CANCELLED = "Order Status: Cancelled";

    private SwingControlsFixture() {
    }

    /**
     * Update a status label's text and keep its accessible name in lock-step.
     *
     * <p>Swing does not propagate {@link javax.swing.JLabel#setText} to the
     * label's accessible name automatically, and the Java Access Bridge reports
     * a control's accessible name — so a test that re-reads the label through
     * JAB after a click only observes the change if the accessible name is
     * updated alongside the visible text. Updating both keeps the on-screen UI
     * and the JAB-visible accessibility tree honest and consistent.
     *
     * @param label  the status label to update.
     * @param status the new status text (also set as the accessible name).
     */
    private static void setStatus(JLabel label, String status) {
        label.setText(status);
        label.getAccessibleContext().setAccessibleName(status);
    }

    /**
     * Build the fixture window on the Swing event-dispatch thread.
     *
     * @return the fully populated, visible {@link JFrame}.
     */
    private static JFrame buildFrame() {
        JFrame frame = new JFrame(WINDOW_TITLE);
        frame.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);

        JPanel controls = new JPanel(new GridLayout(0, 1, 4, 4));

        // Created first so the button action listeners below can mutate it; it
        // is still added to the panel in its original visual position.
        JLabel statusLabel = new JLabel(STATUS_PENDING);
        statusLabel.getAccessibleContext().setAccessibleName(STATUS_PENDING);

        JButton submitButton = new JButton("Submit Order");
        submitButton.getAccessibleContext().setAccessibleName("Submit Order");
        // Actuating the button changes a JAB-observable property (the status
        // label's accessible name), so a test can prove naturo's click reached
        // the real Swing control — verify-after-action through Java Access
        // Bridge, not just recognition.
        submitButton.addActionListener(event -> setStatus(statusLabel, STATUS_SUBMITTED));
        controls.add(submitButton);

        JButton cancelButton = new JButton("Cancel Order");
        cancelButton.getAccessibleContext().setAccessibleName("Cancel Order");
        cancelButton.addActionListener(event -> setStatus(statusLabel, STATUS_CANCELLED));
        controls.add(cancelButton);

        JTextField customerField = new JTextField("Ada Lovelace");
        customerField.getAccessibleContext().setAccessibleName("Customer Name");
        controls.add(customerField);

        JCheckBox expressCheck = new JCheckBox("Express Shipping");
        expressCheck.getAccessibleContext().setAccessibleName("Express Shipping");
        controls.add(expressCheck);

        controls.add(statusLabel);

        DefaultTableModel tableModel = new DefaultTableModel(
                new Object[][] {
                        {"Widget", "2"},
                        {"Gadget", "5"},
                },
                new Object[] {"Item", "Quantity"});
        JTable itemsTable = new JTable(tableModel);
        itemsTable.getAccessibleContext().setAccessibleName("Order Items");

        DefaultMutableTreeNode root = new DefaultMutableTreeNode("Catalog");
        DefaultMutableTreeNode hardware = new DefaultMutableTreeNode("Hardware");
        hardware.add(new DefaultMutableTreeNode("Widget"));
        hardware.add(new DefaultMutableTreeNode("Gadget"));
        root.add(hardware);
        JTree catalogTree = new JTree(root);
        catalogTree.getAccessibleContext().setAccessibleName("Catalog Tree");

        frame.setLayout(new BorderLayout(8, 8));
        frame.add(controls, BorderLayout.NORTH);
        frame.add(new JScrollPane(itemsTable), BorderLayout.CENTER);
        frame.add(new JScrollPane(catalogTree), BorderLayout.SOUTH);

        frame.setSize(420, 460);
        frame.setLocationRelativeTo(null);
        frame.setVisible(true);
        return frame;
    }

    /**
     * Launch the fixture window.
     *
     * @param args ignored.
     */
    public static void main(String[] args) {
        SwingUtilities.invokeLater(SwingControlsFixture::buildFrame);
    }
}
