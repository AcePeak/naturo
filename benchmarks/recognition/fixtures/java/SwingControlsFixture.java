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

    private SwingControlsFixture() {
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

        JButton submitButton = new JButton("Submit Order");
        submitButton.getAccessibleContext().setAccessibleName("Submit Order");
        controls.add(submitButton);

        JButton cancelButton = new JButton("Cancel Order");
        cancelButton.getAccessibleContext().setAccessibleName("Cancel Order");
        controls.add(cancelButton);

        JTextField customerField = new JTextField("Ada Lovelace");
        customerField.getAccessibleContext().setAccessibleName("Customer Name");
        controls.add(customerField);

        JCheckBox expressCheck = new JCheckBox("Express Shipping");
        expressCheck.getAccessibleContext().setAccessibleName("Express Shipping");
        controls.add(expressCheck);

        JLabel statusLabel = new JLabel("Order Status: Pending");
        statusLabel.getAccessibleContext().setAccessibleName("Order Status: Pending");
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
